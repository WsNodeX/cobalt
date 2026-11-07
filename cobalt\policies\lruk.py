"""LRU-K eviction policy.

LRU-K (O'Neil et al., 1993) delays the admission of an entry into the "hot"
set until it has been requested at least *K* times. The recency used for
eviction decisions is the *K-th most recent* reference rather than the most
recent one, which dramatically reduces the damage caused by one-hit-wonder
scans: a single access no longer promotes a cold item to the front of the
queue. This implementation keeps a bounded history (capped at the configured
capacity) and evicts the entry with the oldest K-th reference first.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, Hashable, Optional

from ..core import BaseCache
from ..errors import InvalidConfiguration


class LRUKCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        k: int = 2,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "lruk",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        if k < 1:
            raise InvalidConfiguration("k must be >= 1")
        self._k = k
        self._refs: Dict[Hashable, "deque[int]"] = {}
        self._recency: Dict[Hashable, int] = {}
        self._seq = 0

    def _record(self, key: Hashable) -> None:
        self._seq += 1
        dq = self._refs.setdefault(key, deque(maxlen=self._k))
        dq.append(self._seq)
        self._recency[key] = dq[0]

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        self._record(key)
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if not present:
            self._stats.puts += 1
            if self._maxsize is not None and len(self._data) >= self._maxsize:
                self._evict_one()
            self._store(key, value)
            self._record(key)
        else:
            self._store(key, value)
            self._record(key)

    def _evict_one(self) -> None:
        # Eviction priority:
        #   * entries referenced fewer than K times are "new/cold" and are
        #     evicted before any warmed entry (priority 0);
        #   * among warmed entries, the one with the oldest K-th reference is
        #     evicted first (priority 1).
        best: Optional[Hashable] = None
        best_priority = 2
        best_tie = float("-inf")
        for key, rec in list(self._recency.items()):
            if key not in self._data:
                continue
            n = len(self._refs[key])
            if n < self._k:
                priority = 0
                tie = -self._refs[key][-1]  # evict the least recently used cold entry
            else:
                priority = 1
                tie = rec  # evict the entry with the oldest K-th reference
            if priority < best_priority or (priority == best_priority and tie > best_tie):
                best = key
                best_priority = priority
                best_tie = tie
        if best is None:
            for key in self._data:
                best = key
                break
        if best is not None:
            self._drop(best)
            self._refs.pop(best, None)
            self._recency.pop(best, None)
            self._stats.evictions += 1

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            self._refs.pop(key, None)
            self._recency.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._refs.clear()
        self._recency.clear()
        self._seq = 0
