"""Core abstractions shared by every cobalt cache implementation.

The :class:`BaseCache` class owns the cross-cutting concerns that every eviction
policy needs: an optional capacity, an optional per-entry time-to-live, a
pluggable clock (useful for deterministic tests), and a live :class:`CacheStats`
object. Concrete policies are responsible for the *ordering* structure (an
``OrderedDict``, a frequency table, an ARC quadrant, ...) but they delegate
storage, expiration bookkeeping and statistics to the base class.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, Optional

from .errors import InvalidConfiguration


class Clock:
    """A thin wrapper around a time source so tests can inject a fake clock."""

    def __init__(self, time_func: Optional[Callable[[], float]] = None) -> None:
        self._time = time_func or time.monotonic

    def now(self) -> float:
        return self._time()


@dataclass
class CacheStats:
    """Running counters for a single cache instance."""

    hits: int = 0
    misses: int = 0
    puts: int = 0
    evictions: int = 0

    @property
    def requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.requests == 0:
            return 0.0
        return self.hits / self.requests

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate

    def as_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "puts": self.puts,
            "evictions": self.evictions,
            "requests": self.requests,
            "hit_rate": round(self.hit_rate, 6),
            "miss_rate": round(self.miss_rate, 6),
        }


class BaseCache:
    """Common machinery for all caches.

    Subclasses must override :meth:`get` and :meth:`put` and are encouraged to
    override :meth:`delete` and :meth:`clear` so that their ordering structure
    stays consistent with the value store.
    """

    def __init__(
        self,
        maxsize: Optional[int] = 128,
        ttl: Optional[float] = None,
        time_func: Optional[Callable[[], float]] = None,
        name: str = "cache",
    ) -> None:
        if maxsize is not None and maxsize < 1:
            raise InvalidConfiguration("maxsize must be >= 1 or None (unbounded)")
        if ttl is not None and ttl <= 0:
            raise InvalidConfiguration("ttl must be > 0 or None")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = Clock(time_func)
        self._stats = CacheStats()
        self._data: Dict[Hashable, Any] = {}
        self._expires: Dict[Hashable, Optional[float]] = {}
        self.name = name

    # --- configuration -------------------------------------------------
    @property
    def maxsize(self) -> Optional[int]:
        return self._maxsize

    @property
    def ttl(self) -> Optional[float]:
        return self._ttl

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = CacheStats()

    # --- time helpers --------------------------------------------------
    def _now(self) -> float:
        return self._clock.now()

    def _expire_at(self) -> Optional[float]:
        if self._ttl is None:
            return None
        return self._clock.now() + self._ttl

    def _is_expired(self, key: Hashable) -> bool:
        exp = self._expires.get(key)
        if exp is None:
            return False
        return self._clock.now() >= exp

    # --- storage primitives -------------------------------------------
    def _store(self, key: Hashable, value: Any) -> None:
        self._data[key] = value
        self._expires[key] = self._expire_at()

    def _drop(self, key: Hashable) -> None:
        self._data.pop(key, None)
        self._expires.pop(key, None)

    def _has(self, key: Hashable) -> bool:
        if key not in self._data:
            return False
        if self._is_expired(key):
            return False
        return True

    def _ensure_fresh(self, key: Hashable) -> bool:
        """Return ``True`` if *key* currently holds a live value.

        Expired entries are purged from the value store as a side effect so the
        ordering structure never has to deal with tombstones.
        """
        if key in self._data and self._is_expired(key):
            self._drop(key)
            return False
        return key in self._data

    # --- container protocol -------------------------------------------
    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: Hashable) -> bool:
        return self._has(key)

    def clear(self) -> None:
        self._data.clear()
        self._expires.clear()

    # --- public API ----------------------------------------------------
    def get(self, key: Hashable, default: Any = None) -> Any:
        raise NotImplementedError

    def put(self, key: Hashable, value: Any) -> None:
        raise NotImplementedError

    def peek(self, key: Hashable, default: Any = None) -> Any:
        """Return the value *without* affecting eviction order or TTL refresh."""
        if self._has(key):
            return self._data[key]
        return default

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            return True
        return False

    def __getitem__(self, key: Hashable) -> Any:
        if not self._has(key):
            raise KeyError(key)
        return self.get(key)

    def __setitem__(self, key: Hashable, value: Any) -> None:
        self.put(key, value)
