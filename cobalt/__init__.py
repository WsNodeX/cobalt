"""cobalt -- a zero-dependency Python toolkit for high-quality caching.

cobalt ships a family of eviction policies (FIFO, LRU, LFU, LRU-K, SLRU, ARC
and the admission-controlled W-TinyLFU), a fluent :class:`CacheBuilder`, a
thread-safe facade and a ``@cached`` decorator -- all with no third-party
dependencies and a tiny, readable codebase that is easy to learn from.
"""

from __future__ import annotations

from .builder import CacheBuilder
from .core import BaseCache, CacheStats, Clock
from .decorators import ThreadSafeCache, cached
from .errors import (
    CobaltError,
    InvalidConfiguration,
    KeyNotHashable,
    UnsupportedPolicy,
)
from .policy import Policy, create
from .policies import (
    ARCCache,
    FIFOCache,
    LFUCache,
    LRUCache,
    LRUKCache,
    SLRUCache,
    TinyLfu,
    WTinyLfuCache,
)
from .version import __version__

__all__ = [
    "ARCCache",
    "BaseCache",
    "CacheBuilder",
    "CacheStats",
    "Clock",
    "CobaltError",
    "FIFOCache",
    "InvalidConfiguration",
    "KeyNotHashable",
    "LFUCache",
    "LRUCache",
    "LRUKCache",
    "Policy",
    "SLRUCache",
    "ThreadSafeCache",
    "TinyLfu",
    "UnsupportedPolicy",
    "WTinyLfuCache",
    "__version__",
    "cached",
    "create",
]
