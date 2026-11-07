import unittest

from cobalt import LRUKCache
from cobalt.builder import CacheBuilder
from cobalt.policy import Policy


class TestLRUK(unittest.TestCase):
    def test_cold_item_evicted_before_hot(self):
        # maxsize 3, k=2
        c = LRUKCache(maxsize=3, k=2)
        c.put(1, "a")
        c.put(2, "b")
        c.put(3, "c")
        c.get(1)  # second access -> 1 is "hot" (2 refs)
        c.put(4, "d")  # evict the least K-recently-used cold entry -> 2 (older, 1 ref)
        self.assertIn(1, c)
        self.assertNotIn(2, c)
        self.assertIn(3, c)
        self.assertIn(4, c)

    def test_k_admission_delay(self):
        # With k=3, a key needs 3 references to be "warm"; a single-access key
        # is evicted before a twice-accessed key when space is tight.
        c = LRUKCache(maxsize=2, k=3)
        c.put(1, "a")
        c.put(2, "b")
        c.get(2)  # 2 has 2 refs, 1 has 1 ref
        c.put(3, "c")  # evict 1 (oldest, fewest refs)
        self.assertNotIn(1, c)
        self.assertIn(2, c)
        self.assertIn(3, c)

    def test_invalid_k(self):
        with self.assertRaises(Exception):
            LRUKCache(maxsize=2, k=0)

    def test_builder_roundtrip(self):
        c = CacheBuilder(Policy.LRUK).maximum_size(8).k(3).build()
        self.assertIsInstance(c, LRUKCache)
        self.assertEqual(c._k, 3)

    def test_capacity_bounded(self):
        c = LRUKCache(maxsize=10)
        for i in range(100):
            c.put(i, i)
        self.assertLessEqual(len(c), 10)


if __name__ == "__main__":
    unittest.main()
