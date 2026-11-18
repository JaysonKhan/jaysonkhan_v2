"""Measure a running voice agent relay end to end with the recorded samples (no microphone).

    venv/bin/python manage.py voice_bench --settings=config.settings.dev        # local relay on :8765
    # production (the token must be signed with the prod SECRET_KEY, so run it on the server):
    ssh jaysonkhan "cd /var/www/jaysonkhan/backend && DJANGO_SETTINGS_MODULE=config.settings.prod \
        venv/bin/python manage.py voice_bench --url wss://jaysonkhan.com/demos/voice-agent/ws"

Each run is one real 4-turn call with a barge-in (~40 s). Against OpenAI that costs a few cents,
and it counts toward the relay's per-IP daily limit.
"""

import asyncio

from demos.voice_agent.bench import print_report, run_once
from demos.voice_agent.tokens import issue_token
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "End-to-end latency + barge-in measurement of the voice agent demo relay."

    def add_arguments(self, parser):
        parser.add_argument("--url", default="ws://127.0.0.1:8765/demos/voice-agent/ws")
        parser.add_argument("--runs", type=int, default=1, help="repeat the 4-turn script; each run is a new call")

    def handle(self, *args, url, runs, **options):
        async def measure() -> list[dict]:
            rows: list[dict] = []
            for _ in range(runs):
                await run_once(f"{url}?token={issue_token(settings.SECRET_KEY)}", rows)
            return rows

        print_report(asyncio.run(measure()), write=self.stdout.write)
