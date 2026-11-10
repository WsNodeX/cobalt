import threading
import unittest

from cobalt import CacheBuilder, Policy, ThreadSafeCache


class TestThreadSafe(unittest.TestCase):
    def test_concurrent_reads_writes(self):
        cache = ThreadSafeCache(CacheBuilder(Policy.LRU).maximum_size(200).build())
        errors = []

        def worker(wid):
            try:
                for i in range(500):
                    cache.put((wid, i), i * 2)
                    cache.get((wid, i % 7))
                    cache.peek((wid, i))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertLessEqual(len(cache), 200)

    def test_stats_consistent_under_load(self):
        cache = ThreadSafeCache(CacheBuilder(Policy.LRU).maximum_size(50).build())

        def worker():
            for i in range(1000):
                if i % 3 == 0:
                    cache.put(i, i)
                else:
                    cache.get(i)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        s = cache.stats
        # requests == hits + misses must hold even under concurrency
        self.assertEqual(s.requests, s.hits + s.misses)


if __name__ == "__main__":
    unittest.main()
