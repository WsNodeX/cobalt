"""Ergonomic wrappers: a thread-safe facade and a ``@cached`` decorator."""

from __future__ import annotations

import functools
import threading
from typing import Any, Callable, Hashable, Optional

from .core import BaseCache


class ThreadSafeCache:
    """Wrap any cobalt cache so every operation is guarded by a re-entrant lock.

    The decorator preserves the public surface of the underlying cache so it can
    be used as a drop-in replacement in concurrent code (web servers, worker
    pools, ...).
    """

    def __init__(self, cache: BaseCache) -> None:
        self._cache = cache
        self._lock = threading.RLock()

    def get(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            return self._cache.get(key, default)

    def put(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._cache.put(key, value)

    def peek(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            return self._cache.peek(key, default)

    def delete(self, key: Hashable) -> bool:
        with self._lock:
            return self._cache.delete(key)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def reset_stats(self) -> None:
        with self._lock:
            self._cache.reset_stats()

    @property
    def stats(self):
        with self._lock:
            return self._cache.stats

    @property
    def maxsize(self):
        return self._cache.maxsize

    @property
    def ttl(self):
        return self._cache.ttl

    def __contains__(self, key: Hashable) -> bool:
        with self._lock:
            return key in self._cache

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __getitem__(self, key: Hashable) -> Any:
        with self._lock:
            return self._cache[key]

    def __setitem__(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._cache[key] = value


def cached(cache: BaseCache, key_fn: Optional[Callable[..., Hashable]] = None) -> Callable:
    """Decorate a function so its results are memoised in *cache*.

    By default the cache key is derived from the positional and keyword
    arguments; pass ``key_fn`` to compute a custom key (for example to ignore a
    request object and key only on a user id).
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_fn is not None:
                key = key_fn(*args, **kwargs)
            else:
                key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                return cache.get(key)
            value = fn(*args, **kwargs)
            cache.put(key, value)
            return value

        return wrapper

    return decorator
