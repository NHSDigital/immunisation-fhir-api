import tempfile
import unittest

from local_lambda import load_string


class TestLoadString(unittest.TestCase):
    def test_load_string_reads_file_contents(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write("hello world")
            tmp.seek(0)

            result = load_string(tmp.name)
            self.assertEqual(result, "hello world")

    def test_load_string_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_string("/nonexistent/file/path.py")
