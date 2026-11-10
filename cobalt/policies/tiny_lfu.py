"""TinyLFU frequency sketch.

TinyLFU (Efficient Cache Admission, Gil Einziger et al., 2015) is a compact,
approximate frequency counter used to decide *admission*: when the cache is
full, should a freshly requested item be allowed to evict an incumbent? A
Count-Min sketch with ``depth`` hash functions and 4-bit saturating counters
approximates each key's access frequency using a few hundred bytes. To avoid
holding stale frequencies forever, the sketch *ages*: after ``sample_size``
increments it halves every counter, so a formerly-hot key that went cold loses
its advantage -- this is what lets TinyLFU adapt to shifting workloads.
"""

from __future__ import annotations

import hashlib
from typing import Any, Hashable


class TinyLfu:
    """A Count-Min-style frequency sketch with periodic aging."""

    def __init__(self, sample_size: int = 512, depth: int = 4, seed: int = 0) -> None:
        if sample_size < 1:
            raise ValueError("sample_size must be >= 1")
        if depth < 1:
            raise ValueError("depth must be >= 1")
        self._width = sample_size
        self._depth = depth
        self._table: "list[int]" = [0] * (sample_size * depth)
        self._reset_at = sample_size
        self._size = 0
        self._seed = seed

    @staticmethod
    def _keybytes(key: Hashable) -> bytes:
        if isinstance(key, bytes):
            return key
        if isinstance(key, str):
            return key.encode("utf-8")
        if isinstance(key, int):
            return str(key).encode("ascii")
        return repr(key).encode("utf-8")

    def _indices(self, key: Hashable) -> "list[int]":
        kb = self._keybytes(key)
        digest = hashlib.blake2b(kb, digest_size=8, key=str(self._seed).encode("utf-8")).digest()
        base = int.from_bytes(digest, "big")
        out: "list[int]" = []
        for i in range(self._depth):
            mixed = (base ^ ((base >> 17) * (i + 1))) >> (i * 7)
            out.append(i * self._width + (mixed % self._width))
        return out

    def estimate(self, key: Hashable) -> int:
        idxs = self._indices(key)
        return min(self._table[i] for i in idxs)

    def increment(self, key: Hashable) -> None:
        idxs = self._indices(key)
        m = min(self._table[i] for i in idxs)
        if m < 15:
            for i in idxs:
                if self._table[i] == m:
                    self._table[i] = m + 1
        self._size += 1
        if self._size >= self._reset_at:
            self._reset()

    def _reset(self) -> None:
        for i in range(len(self._table)):
            self._table[i] >>= 1
        self._size = 0

    def reset(self) -> None:
        for i in range(len(self._table)):
            self._table[i] = 0
        self._size = 0
