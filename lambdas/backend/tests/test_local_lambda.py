import os
import tempfile
import unittest

from local_lambda import load_string


class TestLoadString(unittest.TestCase):
    def test_reads_file_contents(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            f.write("hello world")

        self.assertEqual(load_string(path), "hello world")

    def test_raises_if_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_string("/nonexistent/file/path.py")
