import re
import unittest

from common.converter_utils import timestamp_to_rfc3339


class TestTimestampToRfc3339(unittest.TestCase):
    def test_utc_conversion(self):
        self.assertEqual(timestamp_to_rfc3339("20260212T17443700"), "2026-02-12T17:44:37Z")

    def test_bst_conversion(self):
        self.assertEqual(timestamp_to_rfc3339("20260212T17443701"), "2026-02-12T17:44:37+01:00")

    def test_too_short_raises(self):
        with self.assertRaises(ValueError):
            timestamp_to_rfc3339("20260212T1744")

    def test_output_is_rfc3339(self):
        rfc3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")
        self.assertRegex(timestamp_to_rfc3339("20260212T17443700"), rfc3339)

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            timestamp_to_rfc3339(20260212)

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            timestamp_to_rfc3339("")

    def test_unsupported_offset_raises(self):
        with self.assertRaises(ValueError):
            timestamp_to_rfc3339("20260212T17443705")
