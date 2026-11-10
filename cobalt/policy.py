"""Policy registry and a small factory used by the builder."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Type

from .errors import UnsupportedPolicy
from .policies import (
    ARCCache,
    FIFOCache,
    LFUCache,
    LRUCache,
    LRUKCache,
    SLRUCache,
    WTinyLfuCache,
)
from .core import BaseCache


class Policy(str, Enum):
    """The eviction policies supported out of the box."""

    FIFO = "fifo"
    LRU = "lru"
    LFU = "lfu"
    LRUK = "lruk"
    SLRU = "slru"
    ARC = "arc"
    W_TINY_LFU = "wtinylfu"


_REGISTRY: Dict[Policy, Type[BaseCache]] = {
    Policy.FIFO: FIFOCache,
    Policy.LRU: LRUCache,
    Policy.LFU: LFUCache,
    Policy.LRUK: LRUKCache,
    Policy.SLRU: SLRUCache,
    Policy.ARC: ARCCache,
    Policy.W_TINY_LFU: WTinyLfuCache,
}


def create(policy: Any, **kwargs: Any) -> BaseCache:
    """Instantiate a cache for *policy* (name or :class:`Policy`)."""
    try:
        p = policy if isinstance(policy, Policy) else Policy(str(policy).lower())
    except ValueError:
        raise UnsupportedPolicy(f"unknown policy: {policy!r}")
    cls = _REGISTRY.get(p)
    if cls is None:
        raise UnsupportedPolicy(f"unknown policy: {policy!r}")
    return cls(**kwargs)
