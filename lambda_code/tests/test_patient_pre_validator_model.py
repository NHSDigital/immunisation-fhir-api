"""Test patient pre validation rules on the model"""
import unittest
import os
import json
from copy import deepcopy
from pydantic import ValidationError


from models.fhir_patient import PatientValidator
from .utils import GenericValidatorModelTests


class TestPatientModelPreValidationRules(unittest.TestCase):
    """
    Test patient pre validation rules on the model

    Notes:-
    TypeErrors and ValueErrors are caught and converted to ValidationErrors by pydantic. When
    this happens, the error message is suffixed with the type of error e.g. type_error or
    value_error. This is why the tests check for the type of error in the error message.

    """

    @classmethod
    def setUpClass(cls):
        """Set up for the tests. This only runs once when the class is instantiated"""
        # Set up the path for the sample data
        cls.data_path = f"{os.path.dirname(os.path.abspath(__file__))}/sample_data"

        # set up the sample patient event JSON data
        cls.patient_file_path = f"{cls.data_path}/sample_patient_event.json"
        with open(cls.patient_file_path, "r", encoding="utf-8") as f:
            cls.json_data = json.load(f)

        # set up the untouched sample patient event JSON data
        cls.untouched_patient_json_data = deepcopy(cls.json_data)

        # set up the validator and add custom root validators
        cls.validator = PatientValidator()
        cls.validator.add_custom_root_validators()

    def setUp(self):
        """Set up for each test. This runs before every test"""
        # Ensure that good data is not inadvertently amended by the tests
        self.assertEqual(self.untouched_patient_json_data, self.json_data)

    def test_model_pre_validate_valid_name(self):
        """Test pre_validate_name accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["name"],
            valid_items_to_test=[[{"family": "Test"}]],
        )

    def test_model_pre_validate_invalid_name(self):
        """Test pre_validate_name rejects invalid values when in a model"""
        invalid_list_lengths_to_test = [[{"family": "Test"}, {"family": "Test"}]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="name",
            keys_to_access_value=["name"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_list_lengths_to_test,
        )

    def test_model_pre_validate_valid_name_given(self):
        """Test pre_validate_name_given accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["name", 0, "given"],
            valid_items_to_test=[["Test"], ["Test test"]],
        )

    def test_model_pre_validate_invalid_name_given(self):
        """Test pre_validate_name_given rejects invalid values when in a model"""
        invalid_lists = [
            [1],
            [False],
            [["Test1"]],
        ]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="name[0] -> given",
            keys_to_access_value=["name", 0, "given"],
            predefined_list_length=1,
            invalid_length_lists_to_test=[["Test1", "Test2"]],
            invalid_lists_with_non_string_data_types_to_test=invalid_lists,
        )

    def test_model_pre_validate_valid_name_family(self):
        """Test pre_validate_name_family accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["name", 0, "family"],
            valid_items_to_test=["test"],
        )

    def test_model_pre_validate_invalid_name_family(self):
        """Test pre_validate_name_family rejects invalid values when in a model"""
        GenericValidatorModelTests.string_invalid(
            self,
            field_location="name[0] -> family",
            keys_to_access_value=["name", 0, "family"],
        )

    def test_model_pre_validate_valid_birth_date(self):
        """Test pre_validate_birth_date accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["birthDate"],
            valid_items_to_test=["2000-01-01", "1933-12-31"],
        )

    def test_model_pre_validate_invalid_birth_date(self):
        """Test pre_validate_birth_date rejects invalid values when in a model"""
        GenericValidatorModelTests.date_invalid(
            self, field_location="birthDate", keys_to_access_value=["birthDate"]
        )

    def test_model_pre_validate_valid_gender(self):
        """Test pre_validate_gender accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["gender"],
            valid_items_to_test=["male", "female", "other", "unknown"],
        )

    def test_model_pre_validate_invalid_gender(self):
        """Test pre_validate_gender rejects invalid values when in a model"""
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

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="gender",
            keys_to_access_value=["gender"],
            predefined_values=("male", "female", "other", "unknown"),
            invalid_strings_to_test=invalid_strings_to_test,
        )

    def test_model_pre_validate_valid_address(self):
        """Test pre_validate_address accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["address"],
            valid_items_to_test=[[{"postalCode": "AA1 1AA"}]],
        )

    def test_model_pre_validate_invalid_address(self):
        """Test pre_validate_address rejects invalid values when in a model"""
        GenericValidatorModelTests.list_invalid(
            self,
            field_location="address",
            keys_to_access_value=["address"],
            predefined_list_length=1,
            invalid_length_lists_to_test=[[{"family": "Test"}, {"family": "Test"}]],
        )

    def test_model_pre_validate_valid_address_postal_code(self):
        """Test pre_validate_address_postal_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["address", 0, "postalCode"],
            valid_items_to_test=["AA00 00AA", "A0 0AA"],
        )

    def test_model_pre_validate_invalid_address_postal_code(self):
        """Test pre_validate_address_postal_code rejects invalid values when in a model"""
        # Test invalid data types and empty string
        GenericValidatorModelTests.string_invalid(
            self,
            field_location="address -> postalCode",
            keys_to_access_value=["address", 0, "postalCode"],
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

        invalid_json_data = deepcopy(self.json_data)

        for invalid_address_postal_code in invalid_address_postal_codes:
            invalid_json_data["address"][0]["postalCode"] = invalid_address_postal_code

            # Check that we get the correct error message and that it contains type=value_error
            with self.assertRaises(ValidationError) as error:
                self.validator.validate(invalid_json_data)

            self.assertTrue(
                "address -> postalCode must contain a single space, "
                + "which divides the two parts of the postal code (type=value_error)"
                in str(error.exception)
            )

        # Test invalid address_postal_code length
        invalid_json_data["address"][0]["postalCode"] = "AA000 00AA"

        # Check that we get the correct error message and that it contains type=value_error
        with self.assertRaises(ValidationError) as error:
            self.validator.validate(invalid_json_data)

        self.assertTrue(
            "address -> postalCode must be 8 or fewer characters "
            + "(excluding spaces) (type=value_error)"
            in str(error.exception)
        )
