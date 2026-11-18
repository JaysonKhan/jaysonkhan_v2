"""One call: the browser on one side, the OpenAI Realtime API on the other.

With a WebSocket transport the client owns playback, so the session owns what goes with it:
  * turn state (listening / user speaking / thinking / agent speaking),
  * barge-in: when the user talks over the agent, stop playback in the browser at once and
    truncate the agent's message to the part the user actually heard,
  * per-turn latency: end of the user's speech -> first agent audio byte at this server.
"""

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Protocol

from websockets.asyncio.client import ClientConnection, connect

from .config import VoiceAgentSettings
from .latency import BYTES_PER_MS, AudioClock, Turn
from .protocol import session_update

log = logging.getLogger("voice")

# How far back from the VAD stop point to look for the last speech frame. server_vad stops
# silence_duration_ms after speech; semantic_vad can wait a few seconds after a trailing-off phrase.
SPEECH_END_LOOKBACK_MS = 4000


class BrowserLink(Protocol):
    """The browser end of a call. A Starlette/FastAPI WebSocket satisfies it as is."""

    async def receive(self) -> dict: ...  # ASGI message: websocket.receive / websocket.disconnect

    async def send_text(self, data: str) -> None: ...

    async def send_bytes(self, data: bytes) -> None: ...


@dataclass
class AgentAudio:
    """An agent audio item the browser has received and may still be playing."""

    item_id: str
    sent_ms: float = 0.0
    interrupted: bool = False


class CallSession:
    def __init__(self, browser: BrowserLink, settings: VoiceAgentSettings, max_seconds: float | None = None):
        self.browser = browser
        self.s = settings
        self.max_seconds = max_seconds
        self.clock = AudioClock()
        self.upstream: ClientConnection | None = None
        self._browser_lock = asyncio.Lock()  # two tasks write to the browser socket
        self.turn_count = 0
        self.pending_turn: Turn | None = None  # user finished speaking, reply audio not here yet
        self.agent: AgentAudio | None = None
        self.live_response: str | None = None
        self.dropped_responses: set[str] = set()  # responses cut off by barge-in; late deltas are ignored
        self.barge_in_voice_at: float | None = None

    async def run(self) -> None:
        headers = {"Authorization": f"Bearer {self.s.api_key}"}
        async with connect(self.s.realtime_url, additional_headers=headers, max_size=None) as upstream:
            self.upstream = upstream
            await self._send_up(session_update(self.s))
            tasks = [asyncio.create_task(self._from_browser()), asyncio.create_task(self._from_upstream())]
            done, pending = await asyncio.wait(tasks, timeout=self.max_seconds, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                log.info("call reached its %s s limit", self.max_seconds)
                await self._to_browser({"type": "error", "code": "time_up"})
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()  # surface the error that ended the call, if any

    # ---- browser -> relay ----

    async def _from_browser(self) -> None:
        while True:
            message = await self.browser.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("bytes") is not None:
                pcm = message["bytes"]
                self.clock.push(pcm, time.monotonic())
                await self._send_up({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm).decode()})
            elif message.get("text") is not None:
                await self._on_browser_event(json.loads(message["text"]))

    async def _on_browser_event(self, event: dict) -> None:
        agent = self.agent
        if agent is None or event.get("item_id") != agent.item_id:
            return
        if event["type"] == "playback_stopped":  # browser's answer to our "interrupt"
            await self._finish_barge_in(agent, float(event["played_ms"]))
        elif event["type"] == "playback_done":
            if agent.interrupted:  # playback ran out just as the user started talking
                await self._finish_barge_in(agent, agent.sent_ms)
            else:
                self.agent = None
                await self._state("listening")

    async def _finish_barge_in(self, agent: AgentAudio, played_ms: float) -> None:
        self.agent = None
        heard_ms = int(played_ms)
        if heard_ms < agent.sent_ms:
            # Drop the unheard part, so the model's memory matches what the user actually heard.
            await self._send_up(
                {
                    "type": "conversation.item.truncate",
                    "item_id": agent.item_id,
                    "content_index": 0,
                    "audio_end_ms": heard_ms,
                }
            )
        stop_ms = None
        if self.barge_in_voice_at is not None:
            stop_ms = round((time.monotonic() - self.barge_in_voice_at) * 1000)
        log.info(
            "barge-in  agent silenced %s ms after the user started talking; user heard %d of %d ms sent",
            stop_ms,
            heard_ms,
            agent.sent_ms,
        )
        await self._to_browser(
            {"type": "barge_in", "stop_ms": stop_ms, "heard_ms": heard_ms, "sent_ms": round(agent.sent_ms)}
        )

    # ---- OpenAI -> relay ----

    async def _from_upstream(self) -> None:
        async for raw in self.upstream:
            await self._on_upstream_event(json.loads(raw))

    async def _on_upstream_event(self, event: dict) -> None:
        kind = event["type"]
        if kind == "input_audio_buffer.speech_started":
            await self._on_speech_started(event)
        elif kind == "input_audio_buffer.speech_stopped":
            await self._on_speech_stopped(event)
        elif kind == "response.created":
            self.live_response = event["response"]["id"]
        elif kind == "response.output_audio.delta":
            await self._on_audio_delta(event)
        elif kind in ("response.output_audio.done", "response.output_audio_transcript.delta"):
            if event["response_id"] in self.dropped_responses:
                return
            if kind == "response.output_audio.done":
                await self._to_browser({"type": "agent_audio_done", "item_id": event["item_id"]})
            else:
                await self._to_browser({"type": "agent_text", "item_id": event["item_id"], "delta": event["delta"]})
        elif kind == "conversation.item.input_audio_transcription.completed":
            await self._to_browser({"type": "user_text", "item_id": event["item_id"], "text": event["transcript"]})
        elif kind == "response.done":
            await self._on_response_done(event["response"])
        elif kind == "session.updated":
            log.info("session ready  model=%s", self.s.model)
            await self._to_browser({"type": "ready", "model": self.s.model, "max_seconds": self.max_seconds})
            await self._state("listening")
        elif kind == "error":
            log.warning("realtime error: %s", event["error"])
            await self._to_browser({"type": "error", "code": "upstream", "message": event["error"].get("message", "")})

    async def _on_speech_started(self, event: dict) -> None:
        self.pending_turn = None  # the user kept talking, so an unanswered turn is superseded
        if self.live_response:
            self.dropped_responses.add(self.live_response)  # server VAD cancels it; ignore its stragglers
            self.live_response = None
        await self._state("user_speaking")
        agent = self.agent
        if agent and not agent.interrupted:
            agent.interrupted = True
            voice_ms = self.clock.first_voiced_ms(event["audio_start_ms"], self.clock.total_ms)
            self.barge_in_voice_at = self.clock.arrival_time(
                voice_ms if voice_ms is not None else event["audio_start_ms"]
            )
            await self._to_browser({"type": "interrupt", "item_id": agent.item_id})

    async def _on_speech_stopped(self, event: dict) -> None:
        now = time.monotonic()
        stop_ms = event["audio_end_ms"]
        # Find where the user really stopped: the last speech frame before the VAD stop point.
        voiced_end = self.clock.last_voiced_ms(stop_ms - SPEECH_END_LOOKBACK_MS, stop_ms)
        speech_end_at = self.clock.arrival_time(voiced_end if voiced_end is not None else stop_ms) or now
        self.turn_count += 1
        self.pending_turn = Turn(self.turn_count, speech_end_at, now, speech_end_from_vad=voiced_end is None)
        await self._state("thinking")

    async def _on_audio_delta(self, event: dict) -> None:
        if event["response_id"] in self.dropped_responses:
            return
        pcm = base64.b64decode(event["delta"])
        if self.agent is None or self.agent.item_id != event["item_id"]:
            self.agent = AgentAudio(event["item_id"])
            if self.pending_turn:
                self.pending_turn.first_audio_at = time.monotonic()
                await self._report_turn(self.pending_turn)
                self.pending_turn = None
            await self._to_browser({"type": "agent_audio_start", "item_id": event["item_id"]})
            await self._state("agent_speaking")
        self.agent.sent_ms += len(pcm) / BYTES_PER_MS
        async with self._browser_lock:
            await self.browser.send_bytes(pcm)

    async def _report_turn(self, turn: Turn) -> None:
        m = turn.metrics()
        log.info(
            "turn %d  end of speech -> first audio byte %d ms  (VAD wait %d ms + response %d ms)%s",
            m["turn"],
            m["latency_ms"],
            m["vad_wait_ms"],
            m["response_ms"],
            "  [speech end taken from VAD]" if m["speech_end_from_vad"] else "",
        )
        await self._to_browser({"type": "turn", **m})

    async def _on_response_done(self, response: dict) -> None:
        if response["id"] == self.live_response:
            self.live_response = None
        usage = response.get("usage") or {}
        log.info(
            "response %s  status=%s  tokens in=%s (cached %s) out=%s",
            response["id"],
            response.get("status"),
            usage.get("input_tokens"),
            (usage.get("input_token_details") or {}).get("cached_tokens"),
            usage.get("output_tokens"),
        )

    # ---- helpers ----

    async def _state(self, state: str) -> None:
        await self._to_browser({"type": "state", "state": state})

    async def _to_browser(self, event: dict) -> None:
        async with self._browser_lock:
            await self.browser.send_text(json.dumps(event))

    async def _send_up(self, event: dict) -> None:
        await self.upstream.send(json.dumps(event))
