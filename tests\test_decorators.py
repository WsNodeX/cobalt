import unittest

from cobalt import CacheBuilder, Policy, ThreadSafeCache, cached


class TestDecorators(unittest.TestCase):
    def test_cached_memoizes(self):
        calls = []

        cache = CacheBuilder(Policy.LRU).maximum_size(128).build()

        @cached(cache)
        def fib(n):
            calls.append(n)
            return n if n < 2 else fib(n - 1) + fib(n - 2)

        self.assertEqual(fib(10), 55)
        # Each distinct fib(k) (k in 0..10) is computed exactly once -> 11 calls.
        # Without caching this would be 177; memoization collapses the tree.
        self.assertEqual(len(calls), 11)
        self.assertLess(len(calls), 30)
        self.assertGreater(cache.stats.hits, 0)

    def test_cached_custom_key(self):
        store = {}

        cache = CacheBuilder(Policy.LRU).maximum_size(64).build()

        @cached(cache, key_fn=lambda user_id: user_id)
        def fetch(user_id):
            store[user_id] = store.get(user_id, 0) + 1
            return f"user-{user_id}"

        self.assertEqual(fetch(1), "user-1")
        self.assertEqual(fetch(1), "user-1")
        self.assertEqual(store[1], 1)  # only computed once

    def test_thread_safe_facade(self):
        inner = CacheBuilder(Policy.LRU).maximum_size(64).build()
        safe = ThreadSafeCache(inner)
        safe.put("a", 1)
        self.assertEqual(safe.get("a"), 1)
        self.assertEqual(len(safe), 1)
        self.assertIn("a", safe)
        safe.clear()
        self.assertEqual(len(safe), 0)


if __name__ == "__main__":
    unittest.main()
