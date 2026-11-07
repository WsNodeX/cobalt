import unittest

from cobalt import LFUCache


class TestLFU(unittest.TestCase):
    def test_evicts_least_frequent(self):
        c = LFUCache(maxsize=2)
        c.put(1, "a")
        c.put(2, "b")
        c.get(1)  # freq(1) -> 2, freq(2) -> 1
        c.get(1)  # freq(1) -> 3
        c.put(3, "c")  # evict 2 (lowest freq)
        self.assertIn(1, c)
        self.assertNotIn(2, c)
        self.assertIn(3, c)

    def test_tie_breaks_by_recency(self):
        c = LFUCache(maxsize=1)
        c.put(1, "a")  # freq1 at time t1
        c.put(2, "b")  # must evict; both freq1, 1 is older -> evict 1
        self.assertNotIn(1, c)
        self.assertIn(2, c)

    def test_repeated_access_increases_freq(self):
        c = LFUCache(maxsize=10)
        c.put("x", 1)
        for _ in range(5):
            c.get("x")
        self.assertEqual(c._freq["x"], 6)

    def test_eviction_count(self):
        c = LFUCache(maxsize=2)
        c.put(1, 1)
        c.put(2, 2)
        c.put(3, 3)
        self.assertEqual(c.stats.evictions, 1)
        self.assertEqual(len(c), 2)

    def test_update_keeps_frequency(self):
        c = LFUCache(maxsize=2)
        c.put(1, "a")
        c.get(1)
        c.get(1)  # freq 3
        c.put(2, "b")
        c.put(3, "c")  # evict 2 (freq1)
        self.assertIn(1, c)
        self.assertNotIn(2, c)
        self.assertIn(3, c)


if __name__ == "__main__":
    unittest.main()
