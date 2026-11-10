"""Using cobalt's ``@cached`` decorator to memoize an expensive lookup.

This mirrors the kind of function you would wrap in a web service: a slow
database/HTTP call that is safe to memoize per key. Run with::

    python examples/web_cache.py
"""

import time

from cobalt import CacheBuilder, Policy, cached


# A "slow" data source we want to protect with a cache.
def fetch_user_from_db(user_id):
    time.sleep(0.05)  # pretend this is a network round-trip
    return {"id": user_id, "name": f"user-{user_id}", "vip": user_id % 3 == 0}


# Build a thread-safe LRU cache and attach it via the decorator.
user_cache = CacheBuilder(Policy.LRU).maximum_size(1000).thread_safe().build()


@cached(user_cache, key_fn=lambda user_id: user_id)
def get_user(user_id):
    return fetch_user_from_db(user_id)


def main():
    t0 = time.perf_counter()
    for _ in range(20):
        get_user(42)  # first call hits the DB, the other 19 are cache hits
    elapsed = time.perf_counter() - t0

    print(f"20 lookups of user 42 took {elapsed * 1000:.1f} ms")
    print(f"cache stats: {user_cache.stats.as_dict()}")
    print("first call ~50ms; the remaining 19 were served from memory.")


if __name__ == "__main__":
    main()
