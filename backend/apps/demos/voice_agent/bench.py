"""A scripted caller: recorded speech instead of a microphone, a simulated speaker instead of real playback.

Used by the relay tests and by `manage.py voice_bench`, which measures a running relay end to end:
  * latency: chunk with the user's last voiced sample sent -> first byte of the agent's reply received
  * barge-in: chunk with the first voiced sample of an interruption sent -> "interrupt" received
"""

import asyncio
import json
import statistics
import time
import wave
from pathlib import Path

from websockets.asyncio.client import connect

from .latency import BYTES_PER_MS, FRAME_MS, SAMPLE_RATE, VOICE_DBFS, frame_levels

CHUNK_MS = 20
CHUNK = CHUNK_MS * BYTES_PER_MS
SAMPLES = Path(__file__).parent / "samples"


def read_wav(path: Path) -> bytes:
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SAMPLE_RATE, 1, 2), path
        return w.readframes(w.getnframes())


def voiced_span(pcm: bytes) -> tuple[int, int]:
    """Byte offsets where speech starts and ends (10 ms frames above the VAD threshold)."""
    voiced = [i for i, level in enumerate(frame_levels(pcm)) if level > VOICE_DBFS]
    frame = FRAME_MS * BYTES_PER_MS
    return voiced[0] * frame, (voiced[-1] + 1) * frame


class Caller:
    """A scripted caller: an always-open microphone plus a simulated speaker."""

    def __init__(self, url: str):
        self.url = url
        self.events: list[dict] = []  # JSON events from the server, each stamped with "_t"
        self._speech = b""
        self._sent = 0
        self._span = (0, 0)
        self._said = asyncio.Event()
        self.voice_start_at: float | None = None
        self.speech_end_at: float | None = None
        # simulated speaker
        self.item: str | None = None
        self.item_started_at = 0.0
        self.item_received_ms = 0.0
        self.audio_started = asyncio.Event()
        self.agent_text: dict[str, str] = {}

    async def __aenter__(self) -> "Caller":
        self.ws = await connect(self.url, max_size=None)
        self._tasks = [asyncio.create_task(self._mic()), asyncio.create_task(self._receive())]
        return self

    async def __aexit__(self, *exc) -> None:
        for task in self._tasks:
            task.cancel()
        await self.ws.close()

    def mark(self) -> int:
        return len(self.events)

    async def next_event(self, kind: str, since: int, timeout: float = 20.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for event in self.events[since:]:
                if event["type"] == kind:
                    return event
            await asyncio.sleep(0.01)
        raise TimeoutError(f"no {kind!r} event within {timeout} s")

    async def say(self, pcm: bytes) -> None:
        """Speak an utterance into the microphone; returns once its last sample was sent."""
        self._span = voiced_span(pcm)
        self.voice_start_at = self.speech_end_at = None
        self._sent = 0
        self._said.clear()
        self.audio_started.clear()
        self._speech = pcm
        await self._said.wait()

    async def reply_latency_ms(self, timeout: float = 20.0) -> float:
        """Wait for the agent's reply to the last utterance; ms from end of speech to its first byte."""
        await asyncio.wait_for(self.audio_started.wait(), timeout)
        return (self.item_started_at - self.speech_end_at) * 1000

    async def wait_until_quiet(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while self.item is not None and time.monotonic() < deadline:
            await asyncio.sleep(0.05)

    def played_ms(self, now: float) -> float:
        if self.item is None:
            return 0.0
        return min((now - self.item_started_at) * 1000, self.item_received_ms)

    async def _mic(self) -> None:
        next_at = time.monotonic()
        while True:
            if self._speech:
                chunk = self._speech[self._sent : self._sent + CHUNK]
                await self.ws.send(chunk + bytes(CHUNK - len(chunk)))
                self._sent += CHUNK
                now = time.monotonic()
                if self.voice_start_at is None and self._sent > self._span[0]:
                    self.voice_start_at = now
                if self.speech_end_at is None and self._sent >= self._span[1]:
                    self.speech_end_at = now
                if self._sent >= len(self._speech):
                    self._speech = b""
                    self._said.set()
            else:
                await self.ws.send(bytes(CHUNK))
            next_at += CHUNK_MS / 1000
            await asyncio.sleep(max(0.0, next_at - time.monotonic()))

    async def _receive(self) -> None:
        async for message in self.ws:
            now = time.monotonic()
            if isinstance(message, bytes):
                if self.item_received_ms == 0:
                    self.item_started_at = now
                    self.audio_started.set()
                self.item_received_ms += len(message) / BYTES_PER_MS
                continue
            event = json.loads(message)
            event["_t"] = now
            self.events.append(event)
            kind = event["type"]
            if kind == "agent_audio_start":
                self.item, self.item_received_ms = event["item_id"], 0.0
            elif kind == "agent_text":
                self.agent_text[event["item_id"]] = self.agent_text.get(event["item_id"], "") + event["delta"]
            elif kind == "interrupt":
                stop = {"type": "playback_stopped", "item_id": event["item_id"], "played_ms": self.played_ms(now)}
                self.item = None
                await self.ws.send(json.dumps(stop))
            elif kind == "agent_audio_done" and event["item_id"] == self.item:
                remaining = self.item_received_ms - self.played_ms(now)
                asyncio.create_task(self._finish_playback(event["item_id"], remaining))

    async def _finish_playback(self, item_id: str, remaining_ms: float) -> None:
        await asyncio.sleep(max(0.0, remaining_ms) / 1000)
        if self.item == item_id:
            self.item = None
            await self.ws.send(json.dumps({"type": "playback_done", "item_id": item_id}))


async def run_once(url: str, rows: list[dict]) -> None:
    hello, story, interrupt, recall = (
        read_wav(SAMPLES / name) for name in ("1-hello.wav", "2-story.wav", "3-interrupt.wav", "4-recall.wav")
    )
    async with Caller(url) as caller:
        await caller.next_event("ready", since=0)
        await asyncio.sleep(1.0)

        async def turn(label: str, pcm: bytes) -> dict:
            mark = caller.mark()
            await caller.say(pcm)
            client_ms = await caller.reply_latency_ms()
            server = await caller.next_event("turn", since=mark)
            row = {"label": label, "client_ms": round(client_ms), **server}
            rows.append(row)
            return row

        await turn("short question", hello)
        await caller.wait_until_quiet()

        await turn("ask for a story", story)
        await asyncio.sleep(2.0)  # let the agent talk for a while, then talk over it
        mark = caller.mark()
        await caller.say(interrupt)
        interrupted = await caller.next_event("interrupt", since=mark)
        barge = await caller.next_event("barge_in", since=mark)
        client_ms = await caller.reply_latency_ms()
        server = await caller.next_event("turn", since=mark)
        rows.append({"label": "interruption", "client_ms": round(client_ms), **server})
        rows[-2]["barge_in"] = {
            "client_stop_ms": round((interrupted["_t"] - caller.voice_start_at) * 1000),
            **{k: barge[k] for k in ("stop_ms", "heard_ms", "sent_ms")},
        }
        await caller.wait_until_quiet()

        mark = caller.mark()
        await turn("what did you say last?", recall)
        start = await caller.next_event("agent_audio_start", since=mark)
        await caller.wait_until_quiet()
        rows[-1]["agent_said"] = caller.agent_text.get(start["item_id"], "")


def print_report(rows: list[dict], write=print) -> None:
    write(f"\n{'turn':<24}{'client':>9}{'server':>9}{'VAD wait':>10}{'response':>10}")
    for r in rows:
        write(
            f"{r['label']:<24}{r['client_ms']:>7} ms{r['latency_ms']:>6} ms{r['vad_wait_ms']:>7} ms{r['response_ms']:>7} ms"
        )
        if b := r.get("barge_in"):
            write(
                f"  barge-in: agent stopped {b['client_stop_ms']} ms after the interruption started "
                f"(server: {b['stop_ms']} ms); user heard {b['heard_ms']} of {b['sent_ms']} ms sent"
            )
        if said := r.get("agent_said"):
            write(f"  agent: {said!r}")
    client = [r["client_ms"] for r in rows]
    write(
        f"\nend of speech -> first audio byte, client side: median {statistics.median(client):.0f} ms, "
        f"min {min(client)} ms, max {max(client)} ms over {len(client)} turns"
    )
