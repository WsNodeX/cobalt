"""Command line interface for cobalt.

Usage
-----
    python -m cobalt.cli version
    python -m cobalt.cli demo
    python -m cobalt.cli bench --size 256 --requests 20000
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import List, Optional

from .builder import CacheBuilder
from .policy import Policy
from .version import __version__


def _cmd_version(_args: argparse.Namespace) -> int:
    print(f"cobalt {__version__}")
    return 0


def _cmd_demo(_args: argparse.Namespace) -> int:
    cache = CacheBuilder(Policy.LRU).maximum_size(3).build()
    print("# LRU cache with capacity 3")
    for key in ["a", "b", "c", "a", "d"]:
        before = key in cache
        val = cache.get(key, None)
        if val is None:
            cache.put(key, key.upper())
            print(f"put({key!r}) -> cache={_state(cache)}")
        else:
            print(f"get({key!r}) -> hit, value={val!r} cache={_state(cache)}")
    print(f"stats: {cache.stats.as_dict()}")
    return 0


def _state(cache) -> str:
    return "{" + ", ".join(sorted(repr(k) for k in cache._data)) + "}"


def _cmd_bench(args: argparse.Namespace) -> int:
    size = args.size
    requests = args.requests
    rng = random.Random(1337)

    def workload(n: int) -> List[int]:
        # Zipf-ish skew so that a few keys dominate (realistic locality).
        out: List[int] = []
        for _ in range(n):
            r = rng.random()
            out.append(int(r * r * 1000))
        return out

    seq = workload(requests)
    policies = [Policy.LRU, Policy.LFU, Policy.ARC, Policy.SLRU, Policy.W_TINY_LFU]
    print(f"# benchmark: size={size} requests={requests} (skewed workload)")
    print(f"{'policy':<12}{'hit_rate':>10}{'miss_rate':>11}")
    for p in policies:
        cache = CacheBuilder(p).maximum_size(size).build()
        for k in seq:
            if k in cache:
                cache.get(k)
            else:
                cache.put(k, k)
        s = cache.stats
        print(f"{p.value:<12}{s.hit_rate:>10.4f}{s.miss_rate:>11.4f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cobalt", description="cobalt cache toolkit CLI")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="print the cobalt version")
    sub.add_parser("demo", help="run a short LRU demonstration")
    bench = sub.add_parser("bench", help="run a synthetic benchmark across policies")
    bench.add_argument("--size", type=int, default=256)
    bench.add_argument("--requests", type=int, default=20000)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None or args.command == "version":
        return _cmd_version(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "bench":
        return _cmd_bench(args)
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
