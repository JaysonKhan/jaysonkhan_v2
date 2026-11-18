"""A small stand-in for the OpenAI Realtime WebSocket, for tests and offline runs.

It speaks just enough of the GA protocol: energy-based server VAD (speech_started /
speech_stopped), a reply streamed as response.output_audio.delta faster than real time,
cancellation when the user talks over a reply, and conversation.item.truncate.
The reply is a tone, not speech.

    cd backend/apps && ../venv/bin/python -m demos.tests.fake_realtime   # then VOICE_REALTIME_URL=ws://127.0.0.1:9100
"""

import asyncio
import base64
import itertools
import json
import math
from array import array

from demos.voice_agent.latency import (
    BYTES_PER_MS,
    FRAME_MS,
    SAMPLE_RATE,
    VOICE_DBFS,
    frame_levels,
)
from websockets.asyncio.server import serve

_ids = itertools.count(1)


def tone(ms: int, freq: float = 440.0, level: float = 0.3) -> bytes:
    n = SAMPLE_RATE * ms // 1000
    return array("h", (int(level * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)) for i in range(n))).tobytes()


class FakeRealtime:
    def __init__(self, think_ms: int = 150, reply_ms: int = 3000, silence_ms: int = 500, prefix_ms: int = 300):
        self.think_ms = think_ms
        self.reply_ms = reply_ms
        self.silence_ms = silence_ms
        self.prefix_ms = prefix_ms
        self.truncates: list[dict] = []
        self.session_updates: list[dict] = []

    async def handler(self, ws) -> None:
        pos_ms = 0.0
        speaking = False
        last_voice_ms = 0.0
        user_item = ""
        reply: asyncio.Task | None = None
        leftover = b""

        async def send(event: dict) -> None:
            await ws.send(json.dumps({"event_id": f"event_{next(_ids)}", **event}))

        async def respond() -> None:
            response_id = f"resp_{next(_ids)}"
            item_id = f"item_{next(_ids)}"
            await asyncio.sleep(self.think_ms / 1000)
            await send({"type": "response.created", "response": {"id": response_id, "status": "in_progress"}})
            audio = tone(self.reply_ms)
            chunk = 100 * BYTES_PER_MS
            for i in range(0, len(audio), chunk):
                delta = base64.b64encode(audio[i : i + chunk]).decode()
                await send(
                    {
                        "type": "response.output_audio.delta",
                        "response_id": response_id,
                        "item_id": item_id,
                        "content_index": 0,
                        "delta": delta,
                    }
                )
                await asyncio.sleep(0.02)  # 100 ms of audio every 20 ms: 5x real time
            await send({"type": "response.output_audio.done", "response_id": response_id, "item_id": item_id})
            await send(
                {
                    "type": "response.done",
                    "response": {
                        "id": response_id,
                        "status": "completed",
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                }
            )

        await send({"type": "session.created", "session": {"id": "sess_fake"}})
        async for raw in ws:
            event = json.loads(raw)
            if event["type"] == "session.update":
                self.session_updates.append(event)
                await send({"type": "session.updated", "session": event["session"]})
            elif event["type"] == "conversation.item.truncate":
                self.truncates.append(event)
                await send(
                    {
                        "type": "conversation.item.truncated",
                        "item_id": event["item_id"],
                        "content_index": 0,
                        "audio_end_ms": event["audio_end_ms"],
                    }
                )
            elif event["type"] == "input_audio_buffer.append":
                pcm = leftover + base64.b64decode(event["audio"])
                frame_bytes = FRAME_MS * BYTES_PER_MS
                usable = len(pcm) - len(pcm) % frame_bytes
                leftover = pcm[usable:]
                for level in frame_levels(pcm[:usable]):
                    pos_ms += FRAME_MS
                    if level > VOICE_DBFS:
                        last_voice_ms = pos_ms
                        if not speaking:
                            speaking = True
                            user_item = f"item_{next(_ids)}"
                            await send(
                                {
                                    "type": "input_audio_buffer.speech_started",
                                    "item_id": user_item,
                                    "audio_start_ms": int(max(0.0, pos_ms - FRAME_MS - self.prefix_ms)),
                                }
                            )
                            if reply and not reply.done():
                                reply.cancel()
                    elif speaking and pos_ms - last_voice_ms >= self.silence_ms:
                        speaking = False
                        await send(
                            {
                                "type": "input_audio_buffer.speech_stopped",
                                "item_id": user_item,
                                "audio_end_ms": int(pos_ms),
                            }
                        )
                        await send({"type": "input_audio_buffer.committed", "item_id": user_item})
                        reply = asyncio.create_task(respond())
        if reply:
            reply.cancel()


async def main(port: int = 9100) -> None:
    async with serve(FakeRealtime().handler, "127.0.0.1", port, max_size=None):
        print(f"fake realtime server on ws://127.0.0.1:{port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
