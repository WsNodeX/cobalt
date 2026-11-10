"""Fluent builder for assembling a configured cache in one chain."""

from __future__ import annotations

from typing import Any, Callable, Optional

from .core import BaseCache
from .decorators import ThreadSafeCache
from .policy import Policy, create


class CacheBuilder:
    """A fluent API for constructing a cache.

    Example
    -------
    >>> from cobalt import CacheBuilder
    >>> cache = (CacheBuilder("wtinylfu")
    ...          .maximum_size(1024)
    ...          .expire_after(60)
    ...          .thread_safe()
    ...          .name("sessions")
    ...          .build())
    """

    def __init__(self, policy: Any = Policy.LRU) -> None:
        self._policy = policy
        self._maxsize: Optional[int] = 128
        self._ttl: Optional[float] = None
        self._time_func: Optional[Callable[[], float]] = None
        self._name: Optional[str] = None
        self._k = 2
        self._protected_ratio = 0.8
        self._window_ratio = 0.01
        self._thread_safe = False

    def policy(self, policy: Any) -> "CacheBuilder":
        self._policy = policy
        return self

    def maximum_size(self, n: Optional[int]) -> "CacheBuilder":
        self._maxsize = n
        return self

    def expire_after(self, seconds: Optional[float]) -> "CacheBuilder":
        self._ttl = seconds
        return self

    def clock(self, time_func: Callable[[], float]) -> "CacheBuilder":
        self._time_func = time_func
        return self

    def name(self, n: str) -> "CacheBuilder":
        self._name = n
        return self

    def k(self, n: int) -> "CacheBuilder":
        self._k = n
        return self

    def protected_ratio(self, r: float) -> "CacheBuilder":
        self._protected_ratio = r
        return self

    def window_ratio(self, r: float) -> "CacheBuilder":
        self._window_ratio = r
        return self

    def thread_safe(self, flag: bool = True) -> "CacheBuilder":
        self._thread_safe = flag
        return self

    def build(self) -> BaseCache:
        kwargs: dict = {
            "maxsize": self._maxsize,
            "ttl": self._ttl,
            "time_func": self._time_func,
        }
        if self._name:
            kwargs["name"] = self._name

        p = self._policy if isinstance(self._policy, Policy) else Policy(str(self._policy).lower())
        if p is Policy.LRUK:
            kwargs["k"] = self._k
        elif p is Policy.SLRU:
            kwargs["protected_ratio"] = self._protected_ratio
        elif p is Policy.W_TINY_LFU:
            kwargs["window_ratio"] = self._window_ratio
            kwargs["protected_ratio"] = self._protected_ratio

        cache = create(p, **kwargs)
        if self._thread_safe:
            cache = ThreadSafeCache(cache)
        return cache
