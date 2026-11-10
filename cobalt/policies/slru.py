"""Segmented LRU (SLRU) eviction policy.

SLRU splits the cache into a *probation* segment (newly admitted entries) and a
*protected* segment (entries that have been accessed at least twice). A hit in
the probation segment promotes the entry into the protected segment; when the
protected segment overflows, its least-recently-used member is demoted back to
probation. Eviction always removes from the probation segment first. This two
stage design captures the "one rare access should not displace a frequently
used item" intuition that plain LRU misses.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable, Optional

from ..core import BaseCache


class SLRUCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        protected_ratio: float = 0.8,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "slru",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        if not 0.0 < protected_ratio < 1.0:
            raise ValueError("protected_ratio must be strictly between 0 and 1")
        self._protected_ratio = protected_ratio
        self._probation: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._protected: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._protected_max = max(1, int(maxsize * protected_ratio)) if maxsize else None
        self._probation_max = (maxsize - self._protected_max) if maxsize else None

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        if key in self._protected:
            self._protected.move_to_end(key)
        elif key in self._probation:
            self._probation.pop(key)
            self._protected[key] = True
            self._balance()
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if not present:
            self._stats.puts += 1
            if self._maxsize is not None and len(self._data) >= self._maxsize:
                self._evict_one()
            self._store(key, value)
            self._probation[key] = True
        else:
            self._store(key, value)
            if key in self._probation:
                self._probation.move_to_end(key)
            elif key in self._protected:
                self._protected.move_to_end(key)

    def _evict_one(self) -> None:
        while self._probation:
            k, _ = self._probation.popitem(last=False)
            if k in self._data:
                self._drop(k)
                self._stats.evictions += 1
                return
        while self._protected:
            k, _ = self._protected.popitem(last=False)
            if k in self._data:
                self._drop(k)
                self._stats.evictions += 1
                return

    def _balance(self) -> None:
        if self._protected_max is None:
            return
        while len(self._protected) > self._protected_max and self._protected:
            k, _ = self._protected.popitem(last=False)
            self._probation[k] = True

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            self._probation.pop(key, None)
            self._protected.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._probation.clear()
        self._protected.clear()
