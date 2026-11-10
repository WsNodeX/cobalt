import unittest

from cobalt import CacheStats, LRUCache
from cobalt.errors import InvalidConfiguration

from util import FakeClock


class TestCore(unittest.TestCase):
    def test_cache_stats(self):
        s = CacheStats()
        for _ in range(3):
            s.hits += 1
        s.misses += 1
        self.assertEqual(s.requests, 4)
        self.assertAlmostEqual(s.hit_rate, 0.75)
        self.assertAlmostEqual(s.miss_rate, 0.25)
        d = s.as_dict()
        self.assertEqual(d["hit_rate"], 0.75)

    def test_invalid_maxsize(self):
        with self.assertRaises(InvalidConfiguration):
            LRUCache(maxsize=0)
        with self.assertRaises(InvalidConfiguration):
            LRUCache(maxsize=-5)

    def test_invalid_ttl(self):
        with self.assertRaises(InvalidConfiguration):
            LRUCache(maxsize=4, ttl=0)

    def test_ttl_none_means_no_expiry(self):
        clock = FakeClock()
        c = LRUCache(maxsize=4, ttl=None, time_func=clock.now)
        c.put("k", "v")
        clock.advance(10**9)
        self.assertEqual(c.get("k"), "v")

    def test_clear(self):
        c = LRUCache(maxsize=4)
        c.put(1, 1)
        c.clear()
        self.assertEqual(len(c), 0)
        self.assertIsNone(c.get(1))

    def test_reset_stats(self):
        c = LRUCache(maxsize=4)
        c.put(1, 1)
        c.get(1)
        c.reset_stats()
        self.assertEqual(c.stats.requests, 0)

    def test_peek_does_not_refresh_ttl(self):
        clock = FakeClock()
        c = LRUCache(maxsize=4, ttl=5, time_func=clock.now)
        c.put("k", "v")
        clock.advance(3)
        c.peek("k")  # should NOT refresh the deadline
        clock.advance(3)  # total 6 > 5
        self.assertIsNone(c.get("k"))


if __name__ == "__main__":
    unittest.main()
