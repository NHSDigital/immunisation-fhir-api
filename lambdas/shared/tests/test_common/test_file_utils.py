import unittest

import common.file_utils


class TestFileUtils(unittest.TestCase):
    def test_get_file_key_without_ext(self):
        """Test get_file_key_without_ext returns the expected values"""

        test_cases = [
            ("file_key.csv", "file_key"),
            ("file_key.dat", "file_key"),
            ("file_key", "file_key"),
            ("/mnt/c/dir.a/file_key.csv", "/mnt/c/dir.a/file_key"),
        ]

        for file_key, file_key_without_ext in test_cases:
            with self.subTest():
                self.assertEqual(common.file_utils.get_file_key_without_ext(file_key), file_key_without_ext)
