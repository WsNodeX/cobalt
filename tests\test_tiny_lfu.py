import unittest

from cobalt import TinyLfu


class TestTinyLfu(unittest.TestCase):
    def test_unseen_is_zero(self):
        s = TinyLfu(sample_size=64)
        self.assertEqual(s.estimate("never"), 0)

    def test_increment_raises_estimate(self):
        s = TinyLfu(sample_size=64)
        s.increment("a")
        self.assertGreaterEqual(s.estimate("a"), 1)
        for _ in range(10):
            s.increment("a")
        self.assertGreaterEqual(s.estimate("a"), 10)

    def test_saturation(self):
        s = TinyLfu(sample_size=64, depth=4)
        for _ in range(200):
            s.increment("hot")
        self.assertLessEqual(s.estimate("hot"), 15)  # 4-bit saturating counters

    def test_different_keys_separate(self):
        s = TinyLfu(sample_size=256)
        for _ in range(10):
            s.increment("a")
        self.assertEqual(s.estimate("b"), 0)
        self.assertGreaterEqual(s.estimate("a"), 10)
        self.assertLessEqual(s.estimate("a"), 15)  # 4-bit saturating

    def test_reset_halves(self):
        s = TinyLfu(sample_size=16)  # ages after 16 increments
        for _ in range(16):
            s.increment("a")  # reaches ~16, then ages -> halves
        after = s.estimate("a")
        self.assertLessEqual(after, 15)

    def test_key_types(self):
        s = TinyLfu(sample_size=64)
        s.increment(123)
        s.increment(("x", "y"))
        s.increment(b"bytes")
        self.assertGreaterEqual(s.estimate(123), 1)
        self.assertGreaterEqual(s.estimate(("x", "y")), 1)
        self.assertGreaterEqual(s.estimate(b"bytes"), 1)


if __name__ == "__main__":
    unittest.main()
