"""Shared test helpers."""

from __future__ import annotations


class FakeClock:
    """A deterministic clock for TTL tests."""

    def __init__(self, t: float = 0.0) -> None:
        self._t = t

    def now(self) -> float:
        return self._t

    def advance(self, dt: float) -> None:
        self._t += dt
