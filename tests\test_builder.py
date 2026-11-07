import unittest

from cobalt import (
    ARCCache,
    CacheBuilder,
    FIFOCache,
    LFUCache,
    LRUKCache,
    LRUCache,
    Policy,
    SLRUCache,
    WTinyLfuCache,
    ThreadSafeCache,
)
from cobalt.errors import InvalidConfiguration, UnsupportedPolicy
from cobalt.policy import create


class TestBuilder(unittest.TestCase):
    def test_build_each_policy(self):
        mapping = {
            Policy.FIFO: FIFOCache,
            Policy.LRU: LRUCache,
            Policy.LFU: LFUCache,
            Policy.LRUK: LRUKCache,
            Policy.SLRU: SLRUCache,
            Policy.ARC: ARCCache,
            Policy.W_TINY_LFU: WTinyLfuCache,
        }
        for p, cls in mapping.items():
            with self.subTest(policy=p):
                c = CacheBuilder(p).maximum_size(16).build()
                self.assertIsInstance(c, cls)

    def test_thread_safe_wraps(self):
        c = CacheBuilder(Policy.LRU).maximum_size(8).thread_safe().build()
        self.assertIsInstance(c, ThreadSafeCache)
        c.put(1, 2)
        self.assertEqual(c.get(1), 2)

    def test_name_propagates(self):
        c = CacheBuilder(Policy.LRU).maximum_size(8).name("mysession").build()
        self.assertEqual(c.name, "mysession")

    def test_lruk_param(self):
        c = CacheBuilder(Policy.LRUK).maximum_size(8).k(3).build()
        self.assertEqual(c._k, 3)

    def test_wtinylfu_params(self):
        c = (
            CacheBuilder(Policy.W_TINY_LFU)
            .maximum_size(100)
            .window_ratio(0.02)
            .protected_ratio(0.7)
            .build()
        )
        self.assertEqual(c._window_max, 2)

    def test_create_factory(self):
        c = create("lru", maxsize=4)
        self.assertIsInstance(c, LRUCache)

    def test_unsupported_policy(self):
        with self.assertRaises(UnsupportedPolicy):
            create("nope")

    def test_invalid_maxsize(self):
        with self.assertRaises(InvalidConfiguration):
            CacheBuilder(Policy.LRU).maximum_size(0).build()

    def test_expire_after(self):
        import time

        c = CacheBuilder(Policy.LRU).maximum_size(4).expire_after(0.01).build()
        c.put("x", 1)
        time.sleep(0.02)
        self.assertIsNone(c.get("x"))


if __name__ == "__main__":
    unittest.main()
