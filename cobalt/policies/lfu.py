"""Least-Frequently-Used eviction policy with O(1) bookkeeping.

LFU tracks how often each entry is accessed and evicts the *least frequently
used* one. Ties (equal frequency) are broken by recency -- the entry that
reached that frequency least recently is evicted first. The data structures are
organised so a hit, a miss and an eviction are all constant time: a dictionary
maps each key to its frequency, and a dictionary maps each frequency to an
ordered list of the keys that currently hold it.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Hashable, Optional

from ..core import BaseCache
from ..errors import InvalidConfiguration


class LFUCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "lfu",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        self._freq: Dict[Hashable, int] = {}
        self._freq_lists: "OrderedDict[int, OrderedDict[Hashable, bool]]" = OrderedDict()
        self._min_freq = 0

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        self._touch(key)
        return self._data[key]

    def _touch(self, key: Hashable) -> None:
        f = self._freq.get(key, 0)
        lst = self._freq_lists.get(f)
        if lst is not None:
            lst.pop(key, None)
            if not lst:
                del self._freq_lists[f]
                if self._min_freq == f:
                    self._min_freq = min(self._freq_lists) if self._freq_lists else f + 1
        nf = f + 1
        self._freq[key] = nf
        self._freq_lists.setdefault(nf, OrderedDict())[key] = True

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if not present:
            self._stats.puts += 1
            if self._maxsize is not None and len(self._data) >= self._maxsize:
                self._evict_one()
            self._store(key, value)
            self._freq[key] = 1
            self._freq_lists.setdefault(1, OrderedDict())[key] = True
            self._min_freq = 1
        else:
            self._store(key, value)
            self._touch(key)

    def _evict_one(self) -> None:
        for f in sorted(self._freq_lists.keys()):
            lst = self._freq_lists[f]
            while lst:
                k = next(iter(lst))
                lst.pop(k)
                if k in self._data:
                    self._drop(k)
                    self._freq.pop(k, None)
                    self._stats.evictions += 1
                    if not lst:
                        del self._freq_lists[f]
                    self._min_freq = min(self._freq_lists) if self._freq_lists else 0
                    return
                else:
                    self._freq.pop(k, None)
            if not lst:
                del self._freq_lists[f]

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            f = self._freq.pop(key, None)
            if f is not None and f in self._freq_lists:
                self._freq_lists[f].pop(key, None)
                if not self._freq_lists[f]:
                    del self._freq_lists[f]
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._freq.clear()
        self._freq_lists.clear()
        self._min_freq = 0
