"""Relay settings, read from environment variables (the repo-root .env is loaded by the ASGI app)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceAgentSettings:
    api_key: str
    model: str
    voice: str
    reasoning_effort: str  # "" leaves the field out, for models without reasoning
    vad_silence_ms: int
    realtime_url: str  # overridable so tests and offline runs can point at a fake server
    secret_key: str  # Django SECRET_KEY: call tokens are signed with a key derived from it
    max_concurrent: int
    max_call_seconds: int
    calls_per_ip_per_day: int
    minutes_per_day: int

    @classmethod
    def from_env(cls) -> "VoiceAgentSettings":
        env = os.environ.get
        model = env("VOICE_REALTIME_MODEL", "gpt-realtime-2.1-mini")
        return cls(
            api_key=env("OPENAI_API_KEY", ""),
            model=model,
            voice=env("VOICE_REALTIME_VOICE", "marin"),
            reasoning_effort=env("VOICE_REASONING_EFFORT", "low"),
            vad_silence_ms=int(env("VOICE_VAD_SILENCE_MS", "500")),
            realtime_url=env("VOICE_REALTIME_URL", f"wss://api.openai.com/v1/realtime?model={model}"),
            secret_key=env("DJANGO_SECRET_KEY", "env-key-missing"),  # same default as settings/base.py
            max_concurrent=int(env("VOICE_MAX_CONCURRENT", "2")),
            max_call_seconds=int(env("VOICE_MAX_CALL_SECONDS", "180")),
            calls_per_ip_per_day=int(env("VOICE_CALLS_PER_IP_PER_DAY", "5")),
            minutes_per_day=int(env("VOICE_MINUTES_PER_DAY", "60")),
        )
