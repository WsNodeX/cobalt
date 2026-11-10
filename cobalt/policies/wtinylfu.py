"""W-TinyLFU cache -- the admission-controlled policy behind Caffeine.

W-TinyLFU (Gil Einziger et al., 2015; popularised by the Caffeine Java cache)
combines three ideas:

1. A small LRU *window* absorbs brand-new entries so a single access does not
   immediately displace a long-lived item.
2. The rest of the cache is split into a *probation* and a *protected* segment
   (a segmented-LRU), so entries must prove themselves before becoming
   protected.
3. A :class:`TinyLfu` frequency sketch gates admission: when the window
   overflows, the window's victim is admitted into the probation segment only
   if its estimated frequency *exceeds* that of the probation's least-recently
   used incumbent. This is what gives W-TinyLFU its famously high hit rate
   across both locality-heavy and scan-heavy workloads.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable, Optional

from ..core import BaseCache
from ..errors import InvalidConfiguration
from .tiny_lfu import TinyLfu


class WTinyLfuCache(BaseCache):
    def __init__(
        self,
        maxsize: int = 128,
        window_ratio: float = 0.01,
        protected_ratio: float = 0.8,
        ttl: Optional[float] = None,
        time_func=None,
        name: str = "wtinylfu",
    ) -> None:
        if maxsize is None or maxsize < 1:
            raise InvalidConfiguration("W-TinyLFU requires a concrete maxsize >= 1")
        if not 0.0 < window_ratio < 1.0:
            raise InvalidConfiguration("window_ratio must be strictly between 0 and 1")
        if not 0.0 < protected_ratio < 1.0:
            raise InvalidConfiguration("protected_ratio must be strictly between 0 and 1")
        super().__init__(maxsize, ttl, time_func, name)

        if maxsize == 1:
            self._window_max = 1
            main_max = 0
        else:
            self._window_max = max(1, int(maxsize * window_ratio))
            main_max = maxsize - self._window_max
        self._protected_max = int(main_max * protected_ratio)
        self._probation_max = main_max - self._protected_max

        self._window: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._probation: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._protected: "OrderedDict[Hashable, bool]" = OrderedDict()
        self._sketch = TinyLfu(sample_size=max(64, maxsize * 4))

    def get(self, key: Hashable, default: Any = None) -> Any:
        if not self._ensure_fresh(key):
            self._stats.misses += 1
            return default
        self._stats.hits += 1
        self._sketch.increment(key)
        if key in self._window:
            self._window.move_to_end(key)
        elif key in self._probation:
            self._probation.pop(key)
            self._protected[key] = True
            self._balance()
        elif key in self._protected:
            self._protected.move_to_end(key)
        return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        present = self._ensure_fresh(key)
        if present:
            self._store(key, value)
            if key in self._window:
                self._window.move_to_end(key)
            elif key in self._probation:
                self._probation.move_to_end(key)
            elif key in self._protected:
                self._protected.move_to_end(key)
            return

        self._stats.puts += 1
        self._sketch.increment(key)
        self._store(key, value)
        self._window[key] = True
        self._evict()

    def _evict(self) -> None:
        # 1) Keep the window at its target size by draining the oldest window
        #    entry into the main space using frequency-based admission.
        if len(self._window) > self._window_max:
            ck, _ = self._window.popitem(last=False)
            if len(self._probation) > 0:
                vk = next(iter(self._probation))
                if self._sketch.estimate(ck) > self._sketch.estimate(vk):
                    self._probation.pop(vk)
                    self._drop(vk)
                    self._stats.evictions += 1
                    self._probation[ck] = True
                else:
                    # Admission lost: the candidate is evicted (value discarded).
                    self._drop(ck)
                    self._stats.evictions += 1
            else:
                self._probation[ck] = True

        # 2) Enforce the hard capacity bound.
        while (len(self._window) + len(self._probation) + len(self._protected)) > self._maxsize:
            if len(self._probation) > 0:
                vk, _ = self._probation.popitem(last=False)
                self._drop(vk)
                self._stats.evictions += 1
            elif len(self._protected) > 0:
                vk, _ = self._protected.popitem(last=False)
                self._drop(vk)
                self._stats.evictions += 1
            elif len(self._window) > 0:
                wk, _ = self._window.popitem(last=False)
                self._drop(wk)
                self._stats.evictions += 1
            else:
                break

        self._balance()

    def _balance(self) -> None:
        while len(self._protected) > self._protected_max and self._protected:
            k, _ = self._protected.popitem(last=False)
            self._probation[k] = True

    def delete(self, key: Hashable) -> bool:
        if key in self._data:
            self._drop(key)
            self._window.pop(key, None)
            self._probation.pop(key, None)
            self._protected.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        super().clear()
        self._window.clear()
        self._probation.clear()
        self._protected.clear()
