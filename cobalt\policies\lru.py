"""Least-Recently-Used eviction policy.

Every access (read or write) moves the entry to the *most recently used* end of
an ordered structure. When the cache is full the *least recently used* entry is
evicted. LRU is the default choice for general purpose caching and the backbone
of countless systems from page caches to HTTP proxies.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable, Optional

from ..core import BaseCache


class LRUCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "lru",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        self._od: "OrderedDict[Hashable, bool]" = OrderedDict()

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        self._od.move_to_end(key)
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if not present:
            self._stats.puts += 1
            if self._maxsize is not None and len(self._data) >= self._maxsize:
                self._evict_one()
            self._store(key, value)
            self._od[key] = True
        else:
            self._store(key, value)
            self._od.move_to_end(key)

    def _evict_one(self) -> None:
        while self._od:
            k, _ = self._od.popitem(last=False)
            if k in self._data:
                self._drop(k)
                self._stats.evictions += 1
                return

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            self._od.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._od.clear()
