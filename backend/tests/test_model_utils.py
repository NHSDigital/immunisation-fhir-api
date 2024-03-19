"""Tests for the utils module"""

import unittest

from models.utils.generic_utils import nhs_number_mod11_check


class UtilsTests(unittest.TestCase):
    """Tests for models.utils.generic_utils module"""

    def test_nhs_number_mod11_check(self):
        """Test the nhs_number_mod11_check function"""
        # All of these NHS numbers are valid
        valid_nhs_numbers = [
            "1345678940",  # check digit 11 is 0
            "9990548609",  # PDS example with 0's in the middle
            "9693821998",  # regular example from PDS
        ]

        for valid_nhs_number in valid_nhs_numbers:
            self.assertTrue(nhs_number_mod11_check(valid_nhs_number))

        invalid_nhs_numbers = [
            "9434765911",  # check digit 1 doesn't match result (9)
            "1234567890",  # check digit 10
            "234567890",  # nhs_number too short
            "12345678901",  # nhs_number too long
            "A234567890",  # nhs_number contains non-numeric characters
        ]

        for invalid_nhs_number in invalid_nhs_numbers:
            self.assertFalse(nhs_number_mod11_check(invalid_nhs_number))
