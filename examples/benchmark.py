"""Compare policies on a skewed (Zipf-like) workload.

Run with::

    python examples/benchmark.py --size 512 --requests 50000
"""

import argparse
import random

from cobalt import CacheBuilder, Policy


def make_workload(n, rng):
    out = []
    for _ in range(n):
        r = rng.random()
        out.append(int(r * r * 2000))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--requests", type=int, default=50000)
    args = ap.parse_args()

    rng = random.Random(7)
    seq = make_workload(args.requests, rng)

    policies = [
        Policy.FIFO,
        Policy.LRU,
        Policy.LFU,
        Policy.LRUK,
        Policy.SLRU,
        Policy.ARC,
        Policy.W_TINY_LFU,
    ]
    print(f"size={args.size} requests={args.requests}")
    print(f"{'policy':<12}{'hit_rate':>10}")
    for p in policies:
        cache = CacheBuilder(p).maximum_size(args.size).build()
        for k in seq:
            if k in cache:
                cache.get(k)
            else:
                cache.put(k, k)
        print(f"{p.value:<12}{cache.stats.hit_rate:>10.4f}")


if __name__ == "__main__":
    main()
