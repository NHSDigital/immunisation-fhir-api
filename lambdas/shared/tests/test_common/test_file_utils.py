import unittest

import common.file_utils


class TestFileUtils(unittest.TestCase):
    def test_get_file_key_without_ext(self):
        """Test get_file_key_without_ext returns the expected values"""

        file_key_without_ext = common.file_utils.get_file_key_without_ext("file_key.csv")
        self.assertEqual(file_key_without_ext, "file_key")

        file_key_without_ext = common.file_utils.get_file_key_without_ext("file_key.dat")
        self.assertEqual(file_key_without_ext, "file_key")

        file_key_without_ext = common.file_utils.get_file_key_without_ext("file_key")
        self.assertEqual(file_key_without_ext, "file_key")

        file_key_without_ext = common.file_utils.get_file_key_without_ext("/mnt/c/dir.a/file_key.csv")
        self.assertEqual(file_key_without_ext, "/mnt/c/dir.a/file_key")
