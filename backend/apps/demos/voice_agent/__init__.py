"""Real-time voice agent demo — domain layer (no web framework imports).

    browser --PCM16 frames--> relay --input_audio_buffer.append--> OpenAI Realtime
    browser <--PCM16 frames-- relay <--response.output_audio.delta-- OpenAI Realtime

Modules:
    config    settings read from the environment (the relay runs without Django)
    protocol  Realtime session config and agent instructions
    session   one call: turn state, barge-in + truncation, per-turn latency
    latency   stream position -> arrival time, speech detection, turn metrics
    limits    concurrency / per-IP / daily-minutes guard (every call is paid for)
    tokens    short-lived HMAC call tokens issued by the Django page
    bench     scripted caller used by the tests and `manage.py voice_bench`

Delivery: Django renders the page (presentation/web), the WebSocket is served by
a small ASGI app (presentation/realtime/voice_agent.py) because the site's
Gunicorn sync workers cannot hold WebSockets.
"""
