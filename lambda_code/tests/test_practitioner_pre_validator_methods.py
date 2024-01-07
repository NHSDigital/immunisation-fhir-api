"""Test practitioner pre-validation methods"""

import unittest

from models.practitioner_pre_validators import PractitionerPreValidators
from .utils import GenericValidatorMethodTests


class TestPrePractitionerMethodValidators(unittest.TestCase):
    """Test practitioner pre-validation methods"""

    def test_pre_name_valid(self):
        """Test PractitionerPreValidators.name"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.name,
            valid_items_to_test=[[{"family": "Test"}]],
        )

    def test_pre_name_invalid(self):
        """Test PractitionerPreValidators.name"""
        GenericValidatorMethodTests.list_invalid(
            self,
            validator=PractitionerPreValidators.name,
            field_location="name",
            predefined_list_length=1,
            invalid_length_lists_to_test=[[{"family": "Test"}, {"family": "Test"}]],
        )

    def test_pre_name_given_valid(self):
        """Test PractitionerPreValidators.name_given"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.name_given,
            valid_items_to_test=[["Test"], ["Test test"]],
        )

    def test_pre_name_given_invalid(self):
        """Test PractitionerPreValidators.name_given"""

        invalid_lists = [
            [1],
            [False],
            [["Test1"]],
        ]

        GenericValidatorMethodTests.list_invalid(
            self,
            PractitionerPreValidators.name_given,
            field_location="name[0] -> given",
            predefined_list_length=1,
            invalid_length_lists_to_test=[["Test1", "Test2"]],
            invalid_lists_with_non_string_data_types_to_test=invalid_lists,
        )

    def test_pre_name_family_valid(self):
        """Test PractitionerPreValidators.name_family"""
        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.name_family,
            valid_items_to_test=["test"],
        )

    def test_pre_name_family_invalid(self):
        """Test PractitionerPreValidators.name_family"""
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PractitionerPreValidators.name_family,
            field_location="name[0] -> family",
        )

    def test_pre_identifier_valid(self):
        """Test PractitionerPreValidators.identifier"""

        valid_lists_to_test = [
            [
                {
                    "system": "https://supplierABC/identifiers/vacc",
                    "value": "e045626e-4dc5-4df3-bc35-da25263f901e",
                }
            ]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.identifier,
            valid_items_to_test=valid_lists_to_test,
        )

    def test_pre_identifier_invalid(self):
        """Test PractitionerPreValidators.identifier"""

        valid_list_element = {
            "system": "https://supplierABC/identifiers/vacc",
            "value": "e045626e-4dc5-4df3-bc35-da25263f901e",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=PractitionerPreValidators.identifier,
            field_location="identifier",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_identifier_value_valid(self):
        """Test PractitionerPreValidators.identifier_value"""

        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.identifier_value,
            valid_items_to_test=[
                "e045626e-4dc5-4df3-bc35-da25263f901e",
                "ACME-vacc123456",
                "ACME-CUSTOMER1-vacc123456",
            ],
        )

    def test_pre_identifier_value_invalid(self):
        """Test PractitionerPreValidators.identifier_value"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PractitionerPreValidators.identifier_value,
            field_location="identifier[0] -> value",
        )

    def test_pre_identifier_system_valid(self):
        """Test PractitionerPreValidators.identifier_system"""

        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.identifier_system,
            valid_items_to_test=[
                "https://supplierABC/identifiers/vacc",
                "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
            ],
        )

    def test_pre_identifier_system_invalid(self):
        """Test PractitionerPreValidators.identifier_system"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PractitionerPreValidators.identifier_system,
            field_location="identifier[0] -> system",
        )

    def test_pre_identifier_type_coding_valid(self):
        """Test PractitionerPreValidators.identifier_type_coding"""

        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.identifier_type_coding,
            valid_items_to_test=[[{"display": "test"}]],
        )

    def test_pre_identifier_type_coding_invalid(self):
        """Test PractitionerPreValidators.identifier_type_coding"""

        valid_list_element = {"display": "test"}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=PractitionerPreValidators.identifier_type_coding,
            field_location="identifier[0] -> type -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_identifier_type_coding_display_valid(self):
        """Test PractitionerPreValidators.identifier_type_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=PractitionerPreValidators.identifier_type_coding_display,
            valid_items_to_test=["test"],
        )

    def test_pre_identifier_type_coding_display_invalid(self):
        """Test PractitionerPreValidators.identifier_type_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=PractitionerPreValidators.identifier_type_coding_display,
            field_location="identifier[0] -> type -> coding[0] -> display",
        )
