import unittest

from common.validator.lookup_expressions.key_data import KeyData


class TestKeyData(unittest.TestCase):
    """
    Unit tests for the KeyData lookup class to ensure correct key code validation
    """

    def setUp(self):
        self.kd = KeyData()

    def test_site_valid_code(self):
        self.assertTrue(self.kd.find_key("Site", "368208006"))

    def test_site_invalid_code(self):
        self.assertFalse(self.kd.find_key("Site", "not_a_code"))

    def test_route_valid_code(self):
        # pick one known code from route list
        self.assertTrue(self.kd.find_key("Route", "54471007"))

    def test_route_invalid_code(self):
        self.assertFalse(self.kd.find_key("Route", "000000"))

    def test_procedure_valid_code(self):
        self.assertTrue(self.kd.find_key("Procedure", "956951000000104"))

    def test_procedure_invalid_code(self):
        self.assertFalse(self.kd.find_key("Procedure", "956951000000105"))

    def test_organisation_valid_code(self):
        self.assertTrue(self.kd.find_key("Organisation", "RJ1"))

    def test_organisation_invalid_code(self):
        self.assertFalse(self.kd.find_key("Organisation", "RJX"))

    def test_unknown_key_source_returns_false(self):
        self.assertFalse(self.kd.find_key("Unknown", "anything"))

    def test_non_string_inputs_are_handled(self):
        # ensure method is resilient and returns False for non-string without raising
        self.assertFalse(self.kd.find_key("Site", None))
        self.assertFalse(self.kd.find_key("Route", 12345))


if __name__ == "__main__":
    unittest.main()
