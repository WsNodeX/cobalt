"""First-In First-Out eviction policy.

The simplest possible policy: the entry inserted *earliest* is the one evicted
first. Reads never change the ordering, which makes FIFO predictable but blind
to access frequency -- a property that is sometimes exactly what you want for
streaming or write-through workloads.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Hashable, Optional

from ..core import BaseCache


class FIFOCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "fifo",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        self._order: deque = deque()

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if not present:
            self._stats.puts += 1
            if self._maxsize is not None and len(self._data) >= self._maxsize:
                self._evict_one()
            self._store(key, value)
            self._order.append(key)
        else:
            # Refresh TTL but keep the original insertion position.
            self._store(key, value)

    def _evict_one(self) -> None:
        while self._order:
            k = self._order.popleft()
            if k in self._data:
                self._drop(k)
                self._stats.evictions += 1
                return

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            try:
                self._order.remove(key)
            except ValueError:
                pass
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._order.clear()
