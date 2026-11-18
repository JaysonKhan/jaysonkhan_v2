"""The real ASGI relay, driven by the scripted caller, against the fake Realtime server."""

import asyncio
import json
from dataclasses import replace
from unittest import IsolatedAsyncioTestCase

import uvicorn
from demos.voice_agent.bench import Caller
from demos.voice_agent.config import VoiceAgentSettings
from demos.voice_agent.latency import BYTES_PER_MS
from demos.voice_agent.tokens import issue_token
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from presentation.realtime.voice_agent import WS_PATH, create_app

from .fake_realtime import FakeRealtime, tone

SECRET = "relay-test-secret"


def silence(ms: int) -> bytes:
    return bytes(ms * BYTES_PER_MS)


class VoiceRelayTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeRealtime(think_ms=150, reply_ms=3000, silence_ms=500)
        self.upstream = await serve(self.fake.handler, "127.0.0.1", 0, max_size=None)
        self.settings = VoiceAgentSettings(
            api_key="test-key",
            model="gpt-realtime-2.1-mini",
            voice="marin",
            reasoning_effort="low",
            vad_silence_ms=500,
            realtime_url=f"ws://127.0.0.1:{self.upstream.sockets[0].getsockname()[1]}",
            secret_key=SECRET,
            max_concurrent=2,
            max_call_seconds=60,
            calls_per_ip_per_day=5,
            minutes_per_day=60,
        )

    async def asyncTearDown(self):
        if getattr(self, "server", None):
            self.server.should_exit = True
            await self.task
        self.upstream.close()
        await self.upstream.wait_closed()

    async def start_relay(self, settings: VoiceAgentSettings) -> str:
        self.server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=0, log_level="warning"))
        self.task = asyncio.create_task(self.server.serve())
        while not self.server.started:
            await asyncio.sleep(0.01)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}{WS_PATH}"

    async def call(self, settings: VoiceAgentSettings | None = None) -> Caller:
        base = await self.start_relay(settings or self.settings)
        caller = Caller(f"{base}?token={issue_token(SECRET)}")
        await caller.__aenter__()
        self.addAsyncCleanup(caller.__aexit__)
        await caller.next_event("ready", since=0, timeout=5)
        return caller

    async def test_latency_is_measured_from_end_of_speech(self):
        caller = await self.call()
        mark = caller.mark()
        await caller.say(silence(100) + tone(400) + silence(100))
        client_ms = await caller.reply_latency_ms(timeout=5)
        turn = await caller.next_event("turn", since=mark)

        session = self.fake.session_updates[0]["session"]
        self.assertEqual(session["audio"]["input"]["turn_detection"]["type"], "server_vad")
        # The fake VAD needs 500 ms of silence, then "thinks" for 150 ms before the first audio byte.
        self.assertTrue(480 <= turn["vad_wait_ms"] <= 560, turn)
        self.assertTrue(140 <= turn["response_ms"] <= 250, turn)
        self.assertEqual(turn["latency_ms"], turn["vad_wait_ms"] + turn["response_ms"])
        self.assertFalse(turn["speech_end_from_vad"])
        self.assertLess(abs(client_ms - turn["latency_ms"]), 50)  # localhost: client and server agree

    async def test_barge_in_stops_playback_and_truncates_to_what_was_heard(self):
        caller = await self.call()
        await caller.say(tone(400))
        await caller.reply_latency_ms(timeout=5)
        await asyncio.sleep(0.8)  # the user hears ~0.8 s of a 3 s reply, then talks over it
        mark = caller.mark()
        await caller.say(tone(300, freq=300))
        interrupt = await caller.next_event("interrupt", since=mark)
        barge = await caller.next_event("barge_in", since=mark)
        await asyncio.sleep(0.1)  # let the truncate reach the fake

        self.assertEqual([t["item_id"] for t in self.fake.truncates], [interrupt["item_id"]])
        self.assertEqual(self.fake.truncates[0]["audio_end_ms"], barge["heard_ms"])
        self.assertTrue(800 <= barge["heard_ms"] < barge["sent_ms"], barge)
        self.assertLess(barge["stop_ms"], 100)  # the fake VAD fires on the first loud frame

    async def test_call_is_cut_at_the_time_limit(self):
        caller = await self.call(replace(self.settings, max_call_seconds=1))
        ready = caller.events[0]
        self.assertEqual(ready["max_seconds"], 1)
        error = await caller.next_event("error", since=0, timeout=3)
        self.assertEqual(error["code"], "time_up")

    async def first_message(self, url: str) -> dict:
        async with connect(url) as ws:
            return json.loads(await asyncio.wait_for(ws.recv(), 3))

    async def test_calls_without_a_valid_token_never_reach_openai(self):
        base = await self.start_relay(self.settings)
        for url in (base, f"{base}?token=1.2.3", f"{base}?token={issue_token('another-secret')}"):
            self.assertEqual((await self.first_message(url))["code"], "bad_token")
        self.assertEqual(self.fake.session_updates, [])

    async def test_limits_refuse_extra_calls(self):
        base = await self.start_relay(replace(self.settings, max_concurrent=1))
        async with connect(f"{base}?token={issue_token(SECRET)}") as first:
            await asyncio.wait_for(first.recv(), 3)  # the first call is up
            second = await self.first_message(f"{base}?token={issue_token(SECRET)}")
        self.assertEqual(second["code"], "busy")
