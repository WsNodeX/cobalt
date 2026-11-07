import unittest

from cobalt import SLRUCache


class TestSLRU(unittest.TestCase):
    def test_promotion_to_protected(self):
        c = SLRUCache(maxsize=3, protected_ratio=0.8)  # protected_max=2, probation_max=1
        c.put(1, "a")
        c.get(1)  # promote 1 -> protected
        self.assertIn(1, c._protected)
        self.assertNotIn(1, c._probation)

    def test_demotion_keeps_capacity(self):
        c = SLRUCache(maxsize=3, protected_ratio=0.8)
        c.put(1, "a")
        c.get(1)  # -> protected
        c.put(2, "b")
        c.get(2)  # -> protected (now 2 protected = protected_max)
        c.put(3, "c")  # probation
        c.get(3)  # promote 3 -> protected, demote LRU protected (1) to probation
        self.assertIn(3, c._protected)
        self.assertIn(1, c._probation)
        self.assertEqual(len(c), 3)

    def test_evicts_from_probation_first(self):
        c = SLRUCache(maxsize=2, protected_ratio=0.5)  # protected_max=1, probation_max=1
        c.put(1, "a")  # probation
        c.put(2, "b")  # probation (size now 2, fits capacity)
        c.put(3, "c")  # evict probation LRU -> 1
        self.assertNotIn(1, c)
        self.assertIn(2, c)
        self.assertIn(3, c)

    def test_invalid_ratio(self):
        with self.assertRaises(ValueError):
            SLRUCache(maxsize=2, protected_ratio=1.0)

    def test_capacity_bounded(self):
        c = SLRUCache(maxsize=10)
        for i in range(100):
            c.put(i, i)
            c.get(i)
        self.assertLessEqual(len(c), 10)


if __name__ == "__main__":
    unittest.main()
