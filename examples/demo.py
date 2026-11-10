"""A short, runnable tour of cobalt's policies.

Run with::

    python examples/demo.py
"""

from cobalt import ARCCache, CacheBuilder, LRUCache, Policy, WTinyLfuCache


def tour(name, cache, keys):
    print(f"\n=== {name} (maxsize={cache.maxsize}) ===")
    for k in keys:
        if k in cache:
            cache.get(k)
            print(f"  hit   {k!r}")
        else:
            cache.put(k, k * 10)
            print(f"  miss  {k!r} -> stored {k * 10}")
    print(f"  final stats: {cache.stats.as_dict()}")


def main():
    keys = [1, 2, 3, 1, 4, 2, 5, 1, 2, 3, 4, 5]
    tour("LRU", LRUCache(maxsize=3), keys)
    tour("ARC", ARCCache(maxsize=3), keys)
    tour("W-TinyLFU", WTinyLfuCache(maxsize=3), keys)
    tour("LRU-K(k=2)", CacheBuilder(Policy.LRUK).maximum_size(3).k(2).build(), keys)

    print("\n=== TTL + thread-safe builder ===")
    import time

    c = CacheBuilder(Policy.LRU).maximum_size(2).expire_after(0.2).thread_safe().build()
    c.put("x", "short-lived")
    print("  immediately:", c.get("x"))
    time.sleep(0.3)
    print("  after ttl  :", c.get("x", "<expired>"))


if __name__ == "__main__":
    main()
