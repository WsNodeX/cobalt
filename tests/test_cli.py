import contextlib
import io
import unittest

from cobalt import cli
from cobalt.version import __version__


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_version(self):
        rc, out = self._run(["version"])
        self.assertEqual(rc, 0)
        self.assertIn(__version__, out)

    def test_demo(self):
        rc, out = self._run(["demo"])
        self.assertEqual(rc, 0)
        self.assertIn("LRU", out)

    def test_bench(self):
        rc, out = self._run(["bench", "--size", "64", "--requests", "2000"])
        self.assertEqual(rc, 0)
        self.assertIn("policy", out)
        self.assertIn("hit_rate", out)

    def test_no_command_defaults_to_version(self):
        rc, out = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn(__version__, out)


if __name__ == "__main__":
    unittest.main()
