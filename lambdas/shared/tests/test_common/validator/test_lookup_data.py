import unittest

from common.validator.lookup_expressions.lookup_data import LookUpData


class TestLookUpData(unittest.TestCase):
    """
    Unit tests for the LookUpData lookup class to ensure correct lookup code validation
    """

    def setUp(self):
        self.lookup = LookUpData()

    def test_valid_lookup_returns_text(self):
        self.assertEqual(self.lookup.find_lookup("368208006"), "Left upper arm structure")

    def test_unknown_code_returns_empty_string(self):
        self.assertEqual(self.lookup.find_lookup("not_a_code"), "")

    def test_none_returns_empty_string(self):
        self.assertEqual(self.lookup.find_lookup(None), "")

    def test_non_string_input_returns_empty_string(self):
        self.assertEqual(self.lookup.find_lookup(12345), "")


if __name__ == "__main__":
    unittest.main()
