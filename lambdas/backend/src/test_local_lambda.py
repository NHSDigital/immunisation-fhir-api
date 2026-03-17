import tempfile
import unittest

from local_lambda import load_string


class TestLoadString(unittest.TestCase):
    def test_load_string_reads_file_contents(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=True) as tmp:
            tmp.write("hello world")
            tmp.seek(0)

            result = load_string(tmp.name)

            self.assertEqual(result, "hello world")


if __name__ == "__main__":
    unittest.main()
