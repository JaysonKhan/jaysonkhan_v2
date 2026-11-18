"""Pure-Python parts of the voice agent demo: latency math, call limits, call tokens."""

from unittest import TestCase

from demos.voice_agent.latency import BYTES_PER_MS, AudioClock, Turn, frame_levels
from demos.voice_agent.limits import CallLimiter, LimitReached
from demos.voice_agent.tokens import issue_token, verify_token

from .fake_realtime import tone


def silence(ms: int) -> bytes:
    return bytes(ms * BYTES_PER_MS)


class AudioClockTest(TestCase):
    def test_frame_levels_tell_tone_from_silence(self):
        levels = frame_levels(silence(30) + tone(30))
        self.assertEqual(len(levels), 6)
        self.assertTrue(all(level == -120.0 for level in levels[:3]))
        self.assertTrue(all(level > -20 for level in levels[3:]))

    def test_arrival_time_maps_stream_position_to_chunk(self):
        clock = AudioClock()
        for i in range(5):  # five 20 ms chunks arriving at t = 0, 1, 2, 3, 4
            clock.push(silence(20), arrived_at=float(i))
        self.assertEqual(clock.total_ms, 100)
        self.assertEqual(clock.arrival_time(0), 0.0)
        self.assertEqual(clock.arrival_time(20), 0.0)  # last sample of the first chunk
        self.assertEqual(clock.arrival_time(21), 1.0)
        self.assertEqual(clock.arrival_time(99), 4.0)
        self.assertIsNone(clock.arrival_time(150))  # not received yet

    def test_voiced_span_inside_window(self):
        clock = AudioClock()
        clock.push(silence(200) + tone(300) + silence(500), arrived_at=0.0)
        self.assertEqual(clock.first_voiced_ms(0, 1000), 200)
        self.assertEqual(clock.last_voiced_ms(0, 1000), 500)
        self.assertIsNone(clock.last_voiced_ms(600, 1000))

    def test_old_audio_is_forgotten(self):
        clock = AudioClock(keep_ms=100)
        for i in range(10):
            clock.push(tone(20), arrived_at=float(i))
        self.assertEqual(clock.total_ms, 200)
        self.assertIsNone(clock.arrival_time(50))  # trimmed
        self.assertEqual(clock.arrival_time(190), 9.0)
        self.assertEqual(clock.first_voiced_ms(0, 200), 100)  # only the last 100 ms are kept

    def test_turn_metrics_parts_add_up(self):
        turn = Turn(number=1, speech_end_at=10.0, vad_stop_at=10.55, first_audio_at=10.85)
        self.assertEqual(
            turn.metrics(),
            {"turn": 1, "latency_ms": 850, "vad_wait_ms": 550, "response_ms": 300, "speech_end_from_vad": False},
        )


class CallLimiterTest(TestCase):
    def setUp(self):
        self.now = 1_800_000_000.0  # a fixed UTC moment
        self.limiter = CallLimiter(max_concurrent=2, calls_per_ip_per_day=3, minutes_per_day=10, clock=lambda: self.now)

    def refused(self, ip: str) -> str:
        with self.assertRaises(LimitReached) as ctx:
            self.limiter.start(ip)
        return ctx.exception.code

    def test_concurrent_calls_are_capped(self):
        self.limiter.start("1.1.1.1")
        self.limiter.start("2.2.2.2")
        self.assertEqual(self.refused("3.3.3.3"), "busy")

    def test_each_ip_gets_a_few_calls_a_day(self):
        for _ in range(3):
            self.limiter.finish(self.limiter.start("1.1.1.1"))
        self.assertEqual(self.refused("1.1.1.1"), "ip_daily")
        self.limiter.start("2.2.2.2")  # someone else still can

    def test_daily_minutes_budget_stops_new_calls(self):
        ticket = self.limiter.start("1.1.1.1")
        self.now += 10 * 60
        self.limiter.finish(ticket)
        self.assertEqual(self.refused("2.2.2.2"), "daily_budget")

    def test_counters_reset_on_a_new_utc_day(self):
        for _ in range(3):
            self.limiter.finish(self.limiter.start("1.1.1.1"))
        self.now += 24 * 3600
        self.limiter.start("1.1.1.1")
        self.assertEqual(self.limiter.snapshot(), {"active_calls": 1, "minutes_today": 0.0})


class CallTokenTest(TestCase):
    SECRET = "test-secret"

    def test_fresh_token_is_accepted(self):
        self.assertTrue(verify_token(self.SECRET, issue_token(self.SECRET)))

    def test_expired_token_is_refused(self):
        token = issue_token(self.SECRET, now=1000.0, ttl=60)
        self.assertTrue(verify_token(self.SECRET, token, now=1059.0))
        self.assertFalse(verify_token(self.SECRET, token, now=1061.0))

    def test_tampered_or_foreign_tokens_are_refused(self):
        token = issue_token(self.SECRET)
        expires, nonce, signature = token.split(".")
        self.assertFalse(verify_token(self.SECRET, f"{int(expires) + 3600}.{nonce}.{signature}"))
        self.assertFalse(verify_token("other-secret", token))
        for junk in ("", "abc", "1.2", "x.y.z"):
            self.assertFalse(verify_token(self.SECRET, junk))
