"""OpenAI Realtime (GA interface) session configuration."""

from .config import VoiceAgentSettings

INSTRUCTIONS = """You are a friendly voice assistant in a live demo of a real-time voice agent on jaysonkhan.com.
Speak naturally and keep most answers to one or two short sentences.
If the user asks for something long, like a story, go ahead and tell it.
If the user interrupts you, stop the previous topic and answer what they just said.
Always reply in the language the user speaks."""


def session_update(s: VoiceAgentSettings) -> dict:
    session = {
        "type": "realtime",
        "instructions": INSTRUCTIONS,
        "output_modalities": ["audio"],
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": 24000},
                "transcription": {"model": "gpt-transcribe"},
                "turn_detection": {
                    "type": "server_vad",
                    "silence_duration_ms": s.vad_silence_ms,
                    "create_response": True,
                    "interrupt_response": True,
                },
            },
            "output": {"format": {"type": "audio/pcm", "rate": 24000}, "voice": s.voice},
        },
    }
    if s.reasoning_effort:
        session["reasoning"] = {"effort": s.reasoning_effort}
    return {"type": "session.update", "session": session}
