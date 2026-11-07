"""Adaptive Replacement Cache (ARC).

ARC (Megiddo & Modha, 2003) maintains four lists:

* ``T1`` -- recent entries seen only once.
* ``T2`` -- frequent entries seen at least twice.
* ``B1`` / ``B2`` -- *ghost* lists holding the keys of entries recently evicted
  from ``T1`` / ``T2`` (no values, only the keys and their recency).

A self-tuning parameter ``p`` tracks the boundary between the recency-focused
and frequency-focused parts of the cache. When a miss lands on a ghost list,
``p`` is nudged in the direction that would have prevented the miss, so ARC
adapts online between LRU-like and LFU-like behaviour without any knob to turn.
This implementation follows the original algorithm closely.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable, Optional

from ..core import BaseCache


class ARCCache(BaseCache):
    def __init__(
        self,
        maxsize: Optional[int] = 128,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "arc",
    ) -> None:
        super().__init__(maxsize, ttl, time_func, name)
        self._p = 0
        self._t1: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._t2: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._b1: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._b2: "OrderedDict[Hashable, bool]" = OrderedDict()

    # -- internal helpers -------------------------------------------------
    def _replace(self, key_in_b2: bool) -> None:
        c = self._maxsize
        if self._t1 and (
            len(self._t1) > self._p
            or (key_in_b2 and len(self._t1) == self._p)
        ):
            k, _ = self._t1.popitem(last=False)
            self._drop(k)
            self._stats.evictions += 1
            self._b1[k] = True
            while len(self._b1) > c:
                self._b1.popitem(last=False)
        else:
            k, _ = self._t2.popitem(last=False)
            self._drop(k)
            self._stats.evictions += 1
            self._b2[k] = True
            while len(self._b2) > c:
                self._b2.popitem(last=False)

    def _enforce_capacity(self) -> None:
        c = self._maxsize
        while (len(self._t1) + len(self._t2)) > c:
            if self._t1:
                k, _ = self._t1.popitem(last=False)
                if k in self._data:
                    self._drop(k)
                    self._stats.evictions += 1
            elif self._t2:
                k, _ = self._t2.popitem(last=False)
                if k in self._data:
                    self._drop(k)
                    self._stats.evictions += 1
            else:
                break

    # -- public API -------------------------------------------------------
    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        if key in self._t1:
            self._t1.pop(key)
            self._t2[key] = True
        elif key in self._t2:
            self._t2.move_to_end(key)
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if present:
            self._store(key, value)
            if key in self._t1:
                self._t1.pop(key)
                self._t2[key] = True
            elif key in self._t2:
                self._t2.move_to_end(key)
            return

        self._stats.puts += 1
        c = self._maxsize
        in_b1 = key in self._b1
        in_b2 = key in self._b2

        if in_b1:
            self._p = min(self._p + max(len(self._b2) // max(len(self._b1), 1), 1), c)
            self._replace(False)
            self._b1.pop(key, None)
            self._t2[key] = True
            self._store(key, value)
        elif in_b2:
            self._p = max(self._p - max(len(self._b1) // max(len(self._b2), 1), 1), 0)
            self._replace(True)
            self._b2.pop(key, None)
            self._t2[key] = True
            self._store(key, value)
        else:
            l1 = len(self._t1) + len(self._b1)
            if l1 == c:
                if len(self._t1) < c:
                    self._b1.popitem(last=False)
                    self._replace(False)
                else:
                    k, _ = self._t1.popitem(last=False)
                    self._drop(k)
                    self._stats.evictions += 1
            elif l1 < c:
                total = len(self._t1) + len(self._t2) + len(self._b1) + len(self._b2)
                if total >= c:
                    if total == 2 * c:
                        self._b2.popitem(last=False)
                    self._replace(False)
            self._t1[key] = True
            self._store(key, value)

        self._enforce_capacity()

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            self._t1.pop(key, None)
            self._t2.pop(key, None)
            self._b1.pop(key, None)
            self._b2.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._t1.clear()
        self._t2.clear()
        self._b1.clear()
        self._b2.clear()
        self._p = 0
