import unittest

from cobalt import LRUCache

from util import FakeClock


class TestLRU(unittest.TestCase):
    def test_evicts_least_recently_used(self):
        c = LRUCache(maxsize=2)
        c.put(1, "a")
        c.put(2, "b")
        c.get(1)  # 1 becomes most-recently-used
        c.put(3, "c")  # should evict 2
        self.assertIn(1, c)
        self.assertNotIn(2, c)
        self.assertIn(3, c)

    def test_update_moves_to_end(self):
        c = LRUCache(maxsize=2)
        c.put(1, "a")
        c.put(2, "b")
        c.put(1, "A")  # update, 1 now MRU
        c.put(3, "c")  # evict 2
        self.assertIn(1, c)
        self.assertIn(3, c)
        self.assertNotIn(2, c)

    def test_getitem_setitem(self):
        c = LRUCache(maxsize=2)
        c[1] = "a"
        self.assertEqual(c[1], "a")
        with self.assertRaises(KeyError):
            _ = c[99]

    def test_ttl(self):
        clock = FakeClock()
        c = LRUCache(maxsize=3, ttl=5, time_func=clock.now)
        c.put("k", "v")
        clock.advance(4)
        self.assertEqual(c.get("k"), "v")
        clock.advance(2)
        self.assertIsNone(c.get("k"))

    def test_stats_hit_rate(self):
        c = LRUCache(maxsize=2)
        c.put(1, 1)
        c.get(1)
        c.get(2)  # miss
        self.assertAlmostEqual(c.stats.hit_rate, 0.5)

    def test_evict_records_stat(self):
        c = LRUCache(maxsize=2)
        c.put(1, 1)
        c.put(2, 2)
        c.put(3, 3)
        self.assertEqual(c.stats.evictions, 1)


if __name__ == "__main__":
    unittest.main()
