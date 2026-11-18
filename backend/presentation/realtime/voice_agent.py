"""ASGI app for the voice agent demo's WebSocket (delivery layer).

Django renders the page; this small Starlette app serves only the WebSocket, because the site's
Gunicorn sync workers cannot hold one. Nginx routes /demos/voice-agent/ws and /health here.

    production (systemd jaysonkhan-voice, security/systemd/jaysonkhan-voice.service):
        uvicorn presentation.realtime.voice_agent:app --uds /run/jaysonkhan-voice/voice.sock
    local:
        cd backend && venv/bin/uvicorn presentation.realtime.voice_agent:app --port 8765
"""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketState

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR / "apps"))  # same import root as config/settings/base.py
ENV_FILE = BACKEND_DIR.parent / ".env"
if os.access(ENV_FILE, os.R_OK):  # local runs; in production systemd passes it (EnvironmentFile, file is 600)
    load_dotenv(ENV_FILE)  # real environment variables win

from demos.voice_agent.config import VoiceAgentSettings  # noqa: E402
from demos.voice_agent.limits import CallLimiter, LimitReached  # noqa: E402
from demos.voice_agent.session import CallSession  # noqa: E402
from demos.voice_agent.tokens import verify_token  # noqa: E402

log = logging.getLogger("voice")

WS_PATH = "/demos/voice-agent/ws"
HEALTH_PATH = "/demos/voice-agent/health"


def client_ip(ws: WebSocket) -> str:
    # Nginx sets X-Real-IP; behind the unix socket there is no peer address (see CLAUDE.md gotcha #7).
    return ws.headers.get("x-real-ip") or (ws.client.host if ws.client else "unknown")


async def _send_error(ws: WebSocket, code: str) -> None:
    try:
        await ws.send_text(json.dumps({"type": "error", "code": code}))
    except Exception:
        pass  # the browser is already gone


async def _close(ws: WebSocket, code: int = 1000) -> None:
    if ws.client_state == WebSocketState.CONNECTED:
        try:
            await ws.close(code=code)
        except Exception:
            pass  # closed from the other side meanwhile


def create_app(settings: VoiceAgentSettings | None = None) -> Starlette:
    s = settings or VoiceAgentSettings.from_env()
    limiter = CallLimiter(s.max_concurrent, s.calls_per_ip_per_day, s.minutes_per_day)

    async def voice_ws(ws: WebSocket) -> None:
        await ws.accept()
        ip = client_ip(ws)
        if not verify_token(s.secret_key, ws.query_params.get("token", "")):
            await _send_error(ws, "bad_token")
            await _close(ws, 1008)
            return
        if not s.api_key:
            log.error("OPENAI_API_KEY is not set")
            await _send_error(ws, "unavailable")
            await _close(ws, 1011)
            return
        try:
            ticket = limiter.start(ip)
        except LimitReached as limit:
            log.info("call refused (%s) for %s", limit.code, ip)
            await _send_error(ws, limit.code)
            await _close(ws, 1008)
            return
        log.info("call started  ip=%s  %s", ip, limiter.snapshot())
        try:
            await CallSession(ws, s, max_seconds=s.max_call_seconds).run()
        except Exception:  # one failed call must not take the relay down
            log.exception("call failed")
            await _send_error(ws, "unavailable")
        finally:
            limiter.finish(ticket)
            await _close(ws)
            log.info("call ended  %s", limiter.snapshot())

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "configured": bool(s.api_key), **limiter.snapshot()})

    return Starlette(routes=[WebSocketRoute(WS_PATH, voice_ws), Route(HEALTH_PATH, health)])


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
app = create_app()
