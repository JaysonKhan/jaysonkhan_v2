"""Call limits. Every call is billed to the site owner's OpenAI key, so the public demo is capped.

In-memory on purpose: the relay is a single uvicorn process, and a restart resetting today's counters
is acceptable. The hard money limit is the OpenAI project's spend limit; this keeps one visitor or a
script from using it up.
"""

import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone


class LimitReached(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code  # "busy" | "ip_daily" | "daily_budget": the page shows a message per code


@dataclass
class CallTicket:
    ip: str
    started_at: float


class CallLimiter:
    def __init__(self, max_concurrent: int, calls_per_ip_per_day: int, minutes_per_day: int, clock=time.time):
        self.max_concurrent = max_concurrent
        self.calls_per_ip_per_day = calls_per_ip_per_day
        self.seconds_per_day = minutes_per_day * 60
        self._clock = clock
        self.active = 0
        self._day = ""
        self._calls_by_ip: Counter[str] = Counter()
        self.seconds_today = 0.0

    def _roll_day(self) -> None:
        day = datetime.fromtimestamp(self._clock(), timezone.utc).date().isoformat()
        if day != self._day:
            self._day = day
            self._calls_by_ip.clear()
            self.seconds_today = 0.0

    def start(self, ip: str) -> CallTicket:
        self._roll_day()
        if self.active >= self.max_concurrent:
            raise LimitReached("busy")
        if self.seconds_today >= self.seconds_per_day:
            raise LimitReached("daily_budget")
        if self._calls_by_ip[ip] >= self.calls_per_ip_per_day:
            raise LimitReached("ip_daily")
        self.active += 1
        self._calls_by_ip[ip] += 1
        return CallTicket(ip, self._clock())

    def finish(self, ticket: CallTicket) -> None:
        self._roll_day()
        self.active -= 1
        self.seconds_today += self._clock() - ticket.started_at

    def snapshot(self) -> dict:
        self._roll_day()
        return {"active_calls": self.active, "minutes_today": round(self.seconds_today / 60, 1)}
