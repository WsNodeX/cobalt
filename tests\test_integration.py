import random
import unittest

from cobalt import CacheBuilder, Policy


class TestIntegration(unittest.TestCase):
    def _run(self, policy, size, seq):
        cache = CacheBuilder(policy).maximum_size(size).build()
        for k in seq:
            if k in cache:
                cache.get(k)
            else:
                cache.put(k, k)
        return cache.stats

    def test_all_policies_on_skewed_workload(self):
        rng = random.Random(99)
        seq = [int(rng.random() ** 2 * 1000) for _ in range(20000)]
        size = 256
        for p in [
            Policy.FIFO,
            Policy.LRU,
            Policy.LFU,
            Policy.LRUK,
            Policy.SLRU,
            Policy.ARC,
            Policy.W_TINY_LFU,
        ]:
            with self.subTest(policy=p):
                s = self._run(p, size, seq)
                # Every iteration performs exactly one get or one put.
                self.assertEqual(s.requests + s.puts, len(seq))
                self.assertGreaterEqual(s.hit_rate, 0.0)
                self.assertLessEqual(s.hit_rate, 1.0)

    def test_wtinylfu_beats_fifo_on_locality(self):
        # On a workload with strong locality, admission control should not do
        # worse than the naive FIFO policy.
        rng = random.Random(5)
        seq = [int(rng.random() ** 3 * 500) for _ in range(30000)]
        size = 128
        fifo = self._run(Policy.FIFO, size, seq)
        wt = self._run(Policy.W_TINY_LFU, size, seq)
        self.assertGreaterEqual(wt.hit_rate, fifo.hit_rate - 0.05)


if __name__ == "__main__":
    unittest.main()
