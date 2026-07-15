"""Rotating pool of Gemini API keys.

Keys die two ways: quota (429) and expiry (401/403 — the AQ.* ephemeral tokens).
Both cool a key off; the pool hands out the next live one. When every key is
cooling, callers get KeyPoolExhausted rather than a silent hang.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


class KeyPoolExhausted(RuntimeError):
    """Every key is rate-limited or expired."""


# Quota resets on a long cycle; a dead ephemeral token never comes back, but
# cooling it beats tracking expiry we can't see from here.
QUOTA_COOLDOWN_S = 60.0
EXPIRY_COOLDOWN_S = 3600.0


@dataclass
class _Key:
    value: str
    cooled_until: float = 0.0
    failures: int = 0
    uses: int = 0

    @property
    def live(self) -> bool:
        return time.monotonic() >= self.cooled_until

    def label(self) -> str:
        return f"{self.value[:10]}…{self.value[-4:]}"


@dataclass
class KeyPool:
    keys: list[_Key] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _cursor: int = 0

    @classmethod
    def from_values(cls, values: list[str]) -> "KeyPool":
        if not values:
            raise ValueError("KeyPool needs at least one key (set GEMINI_API_KEYS)")
        return cls(keys=[_Key(v) for v in values])

    async def acquire(self) -> str:
        """Next live key, round-robin so load spreads instead of hammering key 0."""
        async with self._lock:
            for _ in range(len(self.keys)):
                k = self.keys[self._cursor % len(self.keys)]
                self._cursor += 1
                if k.live:
                    k.uses += 1
                    return k.value
            soonest = min(k.cooled_until for k in self.keys) - time.monotonic()
            raise KeyPoolExhausted(
                f"all {len(self.keys)} keys cooling; next free in {max(soonest, 0):.0f}s"
            )

    async def report(self, value: str, status: int) -> None:
        """Feed an HTTP status back so the pool can cool a bad key."""
        async with self._lock:
            k = next((k for k in self.keys if k.value == value), None)
            if k is None:
                return
            if status == 429:
                k.failures += 1
                k.cooled_until = time.monotonic() + QUOTA_COOLDOWN_S
            elif status in (401, 403):
                k.failures += 1
                k.cooled_until = time.monotonic() + EXPIRY_COOLDOWN_S
            elif 200 <= status < 300:
                k.failures = 0

    @property
    def live_count(self) -> int:
        return sum(1 for k in self.keys if k.live)

    def stats(self) -> list[dict]:
        now = time.monotonic()
        return [
            {
                "key": k.label(),
                "live": k.live,
                "uses": k.uses,
                "failures": k.failures,
                "cooling_for_s": max(0, round(k.cooled_until - now)),
            }
            for k in self.keys
        ]
