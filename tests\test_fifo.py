import unittest

from cobalt import FIFOCache

from util import FakeClock


class TestFIFO(unittest.TestCase):
    def test_evicts_oldest_inserted(self):
        c = FIFOCache(maxsize=2)
        c.put(1, "a")
        c.put(2, "b")
        c.get(1)  # read does NOT change FIFO order
        c.put(3, "c")  # should evict 1 (oldest inserted), keep 2 and 3
        self.assertNotIn(1, c)
        self.assertIn(2, c)
        self.assertIn(3, c)

    def test_stats(self):
        c = FIFOCache(maxsize=2)
        self.assertIsNone(c.get(1))
        c.put(1, "a")
        self.assertEqual(c.get(1), "a")
        self.assertEqual(c.stats.hits, 1)
        self.assertEqual(c.stats.misses, 1)
        self.assertEqual(c.stats.puts, 1)

    def test_ttl_expiry(self):
        clock = FakeClock()
        c = FIFOCache(maxsize=2, ttl=10, time_func=clock.now)
        c.put("k", "v")
        clock.advance(5)
        self.assertEqual(c.get("k"), "v")
        clock.advance(6)
        self.assertIsNone(c.get("k"))
        self.assertNotIn("k", c)

    def test_delete(self):
        c = FIFOCache(maxsize=2)
        c.put(1, "a")
        self.assertTrue(c.delete(1))
        self.assertFalse(c.delete(1))
        self.assertNotIn(1, c)

    def test_unbounded(self):
        c = FIFOCache(maxsize=None)
        for i in range(1000):
            c.put(i, i)
        self.assertEqual(len(c), 1000)

    def test_peek_does_not_count_as_hit(self):
        c = FIFOCache(maxsize=2)
        c.put(1, "a")
        self.assertEqual(c.peek(1), "a")  # peek returns the value
        self.assertEqual(c.stats.hits, 0)  # but does not count as a hit
        self.assertEqual(c.stats.misses, 0)
        self.assertIsNone(c.peek(99))  # absent key -> default


if __name__ == "__main__":
    unittest.main()
