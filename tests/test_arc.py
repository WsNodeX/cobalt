import unittest

from cobalt import ARCCache, LRUCache


class TestARC(unittest.TestCase):
    def test_capacity_bounded(self):
        c = ARCCache(maxsize=100)
        for i in range(500):
            c.put(i, i)
        self.assertLessEqual(len(c), 100)

    def test_hot_key_survives_scan(self):
        # A frequently accessed item should survive a long one-time scan,
        # whereas plain LRU would evict it.
        arc = ARCCache(maxsize=10)
        for i in range(10):
            arc.put(i, i)
        for _ in range(5):
            arc.get(0)  # make key 0 hot -> moves into T2
        for i in range(10, 60):
            arc.put(i, i)  # scan of one-time keys
        self.assertIn(0, arc)

        lru = LRUCache(maxsize=10)
        for i in range(10):
            lru.put(i, i)
        for _ in range(5):
            lru.get(0)
        for i in range(10, 60):
            lru.put(i, i)
        self.assertNotIn(0, lru)  # LRU evicts the hot key under the scan

    def test_hit_moves_to_t2(self):
        c = ARCCache(maxsize=5)
        c.put("x", 1)
        self.assertIn("x", c._t1)
        c.get("x")
        self.assertIn("x", c._t2)
        self.assertNotIn("x", c._t1)

    def test_stats(self):
        c = ARCCache(maxsize=5)
        c.put(1, 1)
        c.get(1)
        c.get(2)  # miss
        self.assertEqual(c.stats.hits, 1)
        self.assertEqual(c.stats.misses, 1)

    def test_delete(self):
        c = ARCCache(maxsize=5)
        c.put(1, 1)
        self.assertTrue(c.delete(1))
        self.assertNotIn(1, c)
        self.assertFalse(c.delete(1))


if __name__ == "__main__":
    unittest.main()
