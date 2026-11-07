import unittest

from cobalt import WTinyLfuCache


class TestWTinyLfu(unittest.TestCase):
    def test_capacity_bounded(self):
        c = WTinyLfuCache(maxsize=50)
        for i in range(500):
            c.put(i, i)
        self.assertLessEqual(len(c), 50)

    def test_hot_key_survives_scan(self):
        import random

        c = WTinyLfuCache(maxsize=100)
        # "hot" is accessed frequently and *interleaved* with a long scan of
        # one-time keys. Because it keeps getting hits, it is promoted into the
        # protected segment and its frequency stays high, so it survives.
        rng = random.Random(1)
        for i in range(5000):
            c.put("hot", "HOT")
            if i % 3 == 0:
                for _ in range(2):
                    c.get("hot")
            else:
                c.put(f"scan{i}", i)
        self.assertIn("hot", c)
        self.assertLessEqual(len(c), 100)

    def test_admission_prefers_frequent(self):
        c = WTinyLfuCache(maxsize=100)
        # "champ" earns a high frequency.
        for _ in range(100):
            c.put("champ", "C")
            for _ in range(3):
                c.get("champ")
        # Fill the cache with one-time keys, then flood beyond capacity.
        for i in range(95):
            c.put(f"cold{i}", i)
        for i in range(200):
            c.put(f"fresh{i}", i)
        self.assertIn("champ", c)
        self.assertLessEqual(len(c), 100)

    def test_stats_recorded(self):
        c = WTinyLfuCache(maxsize=3)
        c.put(1, 1)
        c.get(1)
        c.get(2)
        self.assertEqual(c.stats.hits, 1)
        self.assertEqual(c.stats.misses, 1)

    def test_requires_maxsize(self):
        with self.assertRaises(Exception):
            WTinyLfuCache(maxsize=None)

    def test_capacity_one(self):
        c = WTinyLfuCache(maxsize=1)
        c.put(1, "a")
        c.put(2, "b")
        self.assertEqual(len(c), 1)
        self.assertTrue(c.get(2) == "b" or c.get(1) == "a")


if __name__ == "__main__":
    unittest.main()
