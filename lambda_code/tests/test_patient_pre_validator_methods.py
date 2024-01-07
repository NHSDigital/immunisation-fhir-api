"""Test patient pre-validation methods"""

import unittest

from models.patient_pre_validators import PatientPreValidators
from .utils import GenericValidatorMethodTests


class TestPrePatientMethodValidators(unittest.TestCase):
    """Test patient pre-validation methods"""

    def test_pre_name_valid(self):
        """Test PatientPreValidators.name"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.name,
            valid_items_to_test=[[{"family": "Test"}]],
        )

    def test_pre_name_invalid(self):
        """Test PatientPreValidators.name"""
        GenericValidatorMethodTests.list_invalid(
            self,
            validator=PatientPreValidators.name,
            field_location="name",
            predefined_list_length=1,
            invalid_length_lists_to_test=[[{"family": "Test"}, {"family": "Test"}]],
        )

    def test_pre_name_given_valid(self):
        """Test PatientPreValidators.name_given"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.name_given,
            valid_items_to_test=[["Test"], ["Test test"]],
        )

    def test_pre_name_given_invalid(self):
        """Test PatientPreValidators.name_given"""

        invalid_lists = [
            [1],
            [False],
            [["Test1"]],
        ]

        GenericValidatorMethodTests.list_invalid(
            self,
            PatientPreValidators.name_given,
            field_location="name[0] -> given",
            predefined_list_length=1,
            invalid_length_lists_to_test=[["Test1", "Test2"]],
            invalid_lists_with_non_string_data_types_to_test=invalid_lists,
        )

    def test_pre_name_family_valid(self):
        """Test PatientPreValidators.name_family"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.name_family,
            valid_items_to_test=["test"],
        )

    def test_pre_name_family_invalid(self):
        """Test PatientPreValidators.name_family"""
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PatientPreValidators.name_family,
            field_location="name[0] -> family",
        )

    def test_pre_birth_date_valid(self):
        """Test PatientPreValidators.birth_date"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.birth_date,
            valid_items_to_test=["2000-01-01", "1933-12-31"],
        )

    def test_pre_birth_date_invalid(self):
        """Test PatientPreValidators.birth_date"""

        GenericValidatorMethodTests.date_invalid(
            self, validator=PatientPreValidators.birth_date, field_location="birthDate"
        )

    def test_pre_gender_valid(self):
        """Test PatientPreValidators.gender"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.gender,
            valid_items_to_test=["male", "female", "other", "unknown"],
        )

    def test_pre_gender_invalid(self):
        """Test PatientPreValidators.gender"""

        invalid_strings_to_test = [
            "0",
            "1",
            "2",
            "9",
            "Male",
            "Female",
            "Unknown",
            "Other",
        ]

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PatientPreValidators.gender,
            field_location="gender",
            predefined_values=("male", "female", "other", "unknown"),
            invalid_strings_to_test=invalid_strings_to_test,
        )

    def test_pre_address_valid(self):
        """Test PatientPreValidators.address"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.address,
            valid_items_to_test=[[{"postalCode": "AA0 0AA"}]],
        )

    def test_pre_address_invalid(self):
        """Test PatientPreValidators.address"""
        valid_list_element = {"postalCode": "AA0 0AA"}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=PatientPreValidators.address,
            field_location="address",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_address_postal_code_valid(self):
        """Test PatientPreValidators.address_postal_code"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PatientPreValidators.address_postal_code,
            valid_items_to_test=["AA00 00AA", "A0 0AA"],
        )

    def test_pre_address_postal_code_invalid(self):
        """Test PatientPreValidators.address_postal_code"""

        # Test invalid data types and empty string
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PatientPreValidators.address_postal_code,
            field_location="address -> postalCode",
        )

        # Test address_postal_codes which are not separated into the two parts by a single space
        invalid_address_postal_codes = [
            "SW1  1AA",  # Too many spaces in divider
            "SW 1 1A",  # Too many space dividers
            "AAA0000AA",  # Too few space dividers
            " AA00 00AA",  # Invalid additional space at start
            "AA00 00AA ",  # Invalid additional space at end
            " AA0000AA",  # Space is incorrectly at start
            "AA0000AA ",  # Space is incorrectly at end
        ]

        for invalid_address_postal_code in invalid_address_postal_codes:
            with self.assertRaises(ValueError) as error:
                PatientPreValidators.address_postal_code(invalid_address_postal_code)
            self.assertEqual(
                str(error.exception),
                "address -> postalCode must contain a single space, "
                + "which divides the two parts of the postal code",
            )

        # Test invalid address_postal_code length
        with self.assertRaises(ValueError) as error:
            PatientPreValidators.address_postal_code("AA000 00AA")
        self.assertEqual(
            str(error.exception),
            "address -> postalCode must be 8 or fewer characters (excluding spaces)",
        )
