"""Pre-validation test utilities"""

import unittest
from copy import deepcopy
from decimal import Decimal

from jsonpath_ng.ext import parse
from .generic_utils import (
    test_valid_values_accepted,
    test_invalid_values_rejected,
)
from .values_for_tests import InvalidDataTypes, InvalidValues, ValidValues


class ValidatorModelTests:
    """Generic tests for model validators"""

    @staticmethod
    def test_string_value(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_strings_to_test: list,
        valid_json_data: dict = None,
        defined_length: int = None,
        max_length: int = None,
        invalid_length_strings_to_test: list = None,
        predefined_values: list = None,
        invalid_strings_to_test: list = None,
        spaces_allowed: bool = True,
        invalid_strings_with_spaces_to_test: list = None,
        is_mandatory_fhir: bool = False,
    ):
        """
        Test that a FHIR model accepts valid string values and rejects the following invalid values:
        * All invalid data types
        * If there is a defined_string_length: Strings of invalid length (defined by the argument
            invalid_length_strings_to_test), plus the empty string
        * If there is no defined_string_length: Empty strings
        * If there is a max_length: Strings longer than max length (defined by the argument
            invalid_length_strings_to_test)
        * If there are predefined values: Invalid strings (i.e. not one of the predefined values) as
            defined by the argument invalid_strings_to_test
        * If the field is manadatory in FHIR: Value of None
        * If spaces are not allowed: Strings with spaces, which would be valid without the
            spaces (defined by the argument invalid_strings_with_spaces_to_test)
        * If is a postal code: Postal codes which are not separated into two parts by a single
            space, or which exceed the maximum length of 8 characters (excluding spaces)

        NOTE: No validation of optional arguments will occur if the method is not given a list of
        values to test. This means that:
        * When optional arguments defined_length and max_length are given, the optional argument
            invalid_length_strings_to_test MUST also be given
        * When optional argument predefined_values is given, the optional argument
            invalid_strings_to_test MUST also be given.
        * When optional argument spaces_allowed is given, the optional argument
            invalid_strings_with_spaces_test must also be given
        """

        valid_json_data = deepcopy(test_instance.json_data) if valid_json_data is None else valid_json_data

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, valid_strings_to_test)

        # Set list of invalid data types to test
        invalid_data_types_for_strings = InvalidDataTypes.for_strings
        if is_mandatory_fhir:
            invalid_data_types_for_strings = filter(None, invalid_data_types_for_strings)

        # Test invalid data types
        for invalid_data_type_for_string in invalid_data_types_for_strings:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_string,
                expected_error_message=f"{field_location} must be a string",
            )

        # If there is a predefined string length, then test invalid string lengths,
        # otherwise check the empty string only
        if defined_length:
            for invalid_length_string in invalid_length_strings_to_test:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_length_string,
                    expected_error_message=f"{field_location} must be {defined_length} characters",
                )
        else:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value="",
                expected_error_message=f"{field_location} must be a non-empty string",
            )

        # If there is a max_length, test strings which exceed that length
        if max_length:
            for invalid_length_string in invalid_length_strings_to_test:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_length_string,
                    expected_error_message=f"{field_location} must be {max_length} " + "or fewer characters",
                )

        # If there are predefined values, then test strings which are
        # not in the set of predefined values
        if predefined_values:
            for invalid_string in invalid_strings_to_test:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_string,
                    expected_error_message=f"{field_location} must be one of the following: "
                    + str(", ".join(predefined_values)),
                )

        # If spaces are not allowed, then test strings with spaces
        if not spaces_allowed:
            for invalid_string_with_spaces in invalid_strings_with_spaces_to_test:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_string_with_spaces,
                    expected_error_message=f"{field_location} must not contain spaces",
                )

    @staticmethod
    def test_list_value(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_lists_to_test: list,
        predefined_list_length: int = None,
        valid_list_element=None,
        is_list_of_strings: bool = False,
        is_list_of_dicts: bool = False,
    ):
        """
        Test that a FHIR model accepts valid list values and rejects the following invalid values:
        * All invalid data types
        * If there is a predefined list length: Strings of invalid length, plus the empty list (note
            that a valid list element must be supplied when a predefined list length is given as
            the valid element will be used to populate lists of incorrect length to ensure
            that the error is being raised due to length, not due to use of an invalid list element)
        * If there is no predfined list length: Empty list
        * If is a list of strings: Lists with non-string or empty string elements
        * If is a list of dicts: Lists with non-dict or empty dict elements

        NOTE: No validation of optional arguments will occur if the method is not given a list of
        values to test. This means that:
        * When optional arguments predefined_list_length is given, the optional argument
            invalid_length_lists_to_test MUST also be given
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, valid_lists_to_test)

        # Test invalid data types
        for invalid_data_type_for_list in InvalidDataTypes.for_lists:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_list,
                expected_error_message=f"{field_location} must be an array",
            )

        # If there is a predefined list length, then test the empty list and a list which is
        # larger than the predefined length, otherwise check the empty list only
        if predefined_list_length:
            # Set up list of invalid_length_lists
            list_too_short = []
            for _ in range(predefined_list_length - 1):
                list_too_short.append(valid_list_element)

            list_too_long = []
            for _ in range(predefined_list_length + 1):
                list_too_long.append(valid_list_element)

            invalid_length_lists = [list_too_short, list_too_long]

            if predefined_list_length != 1:  # If is 1 then list_too_short = []
                invalid_length_lists.append([])

            # Test invalid list lengths
            for invalid_length_list in invalid_length_lists:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_length_list,
                    expected_error_message=f"{field_location} must be an array of length "
                    + f"{predefined_list_length}",
                )
        else:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=[],
                expected_error_message=f"{field_location} must be a non-empty array",
            )

        # Tests lists with non-string or empty string elements (if applicable)
        if is_list_of_strings:
            # Test lists with non-string element
            for invalid_list in InvalidValues.for_lists_of_strings_of_length_1:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_list,
                    expected_error_message=f"{field_location} must be an array of strings",
                )

            # Test empty string in list
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=[""],
                expected_error_message=f"{field_location} must be an array of non-empty strings",
            )

        # Tests lists with non-dict or empty dict elements (if applicable)
        if is_list_of_dicts:
            # Test lists with non-dict element
            for invalid_list in InvalidValues.for_lists_of_dicts_of_length_1:
                test_invalid_values_rejected(
                    test_instance,
                    valid_json_data,
                    field_location=field_location,
                    invalid_value=invalid_list,
                    expected_error_message=f"{field_location} must be an array of objects",
                )

            # Test empty dict in list
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=[{}],
                expected_error_message=f"{field_location} must be an array of non-empty objects",
            )

    @staticmethod
    def test_unique_list(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_lists_to_test: list,
        invalid_list_with_duplicates_to_test: list,
        expected_error_message: str,
    ):
        """
        Test that a FHIR model accepts valid lists with unique values and rejects the following
        invalid values:
        * Lists with duplicate values
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, valid_lists_to_test)
        # Test lists with duplicate values
        test_invalid_values_rejected(
            test_instance,
            valid_json_data,
            field_location=field_location,
            invalid_value=invalid_list_with_duplicates_to_test,
            expected_error_message=expected_error_message,
        )

    @staticmethod
    def test_date_value(
        test_instance: unittest.TestCase,
        field_location: str,
    ):
        """
        Test that a FHIR model accepts valid date values and rejects the following invalid values:
        * All invalid data types
        * Invalid date formats
        * Invalid dates
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, ["2000-01-01", "1933-12-31"])

        # Test invalid data types
        for invalid_data_type_for_string in InvalidDataTypes.for_strings:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_string,
                expected_error_message=f"{field_location} must be a string",
            )

        # Test invalid date string formats
        for invalid_date_format in InvalidValues.for_date_string_formats:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_date_format,
                expected_error_message=f"{field_location} must be a valid date string in the " + 'format "YYYY-MM-DD"',
            )

    @staticmethod
    def test_date_time_value(
        test_instance: unittest.TestCase,
        field_location: str,
        is_occurrence_date_time: bool = False,
    ):
        """
        Test that a FHIR model accepts valid date-time values and rejects the following invalid
        values:
        * All invalid data types
        * Invalid date time string formats
        * Invalid date-times
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, ValidValues.for_date_times)

        # Set list of invalid data types to test
        invalid_data_types_for_strings = InvalidDataTypes.for_strings
        if is_occurrence_date_time:
            invalid_data_types_for_strings = filter(None, invalid_data_types_for_strings)

        # Test invalid data types
        for invalid_data_type_for_string in invalid_data_types_for_strings:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_string,
                expected_error_message=f"{field_location} must be a string",
            )

        expected_error_message = (
            f"{field_location} must be a valid datetime in one of the following formats:"
            "- 'YYYY-MM-DD' — Full date only"
            "- 'YYYY-MM-DDThh:mm:ss' — Full date and time without milliseconds"
            "- 'YYYY-MM-DDThh:mm:ss.f' — Full date and time with milliseconds (any level of precision)"
            "- 'YYYY-MM-DDThh:mm:ss%z' — Full date and time with timezone (e.g. +00:00 or +01:00)"
            "- 'YYYY-MM-DDThh:mm:ss.f%z' — Full date and time with milliseconds and timezone"
            "Only '+00:00' and '+01:00' are accepted as valid timezone offsets."
            f"Note that partial dates are not allowed for {field_location} in this service."
        )

        # Test invalid date time string formats
        for invalid_occurrence_date_time in InvalidValues.for_date_time_string_formats:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_occurrence_date_time,
                expected_error_message=expected_error_message,
            )

        # Test invalid date times
        for invalid_occurrence_date_time in InvalidValues.for_date_times:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_occurrence_date_time,
                expected_error_message=expected_error_message,
            )

    @staticmethod
    def test_boolean_value(
        test_instance: unittest.TestCase,
        field_location: str,
    ):
        """Test that a FHIR model accepts valid boolean values and rejects non-boolean values."""

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(test_instance, valid_json_data, field_location, [True, False])

        # Test invalid data types
        for invalid_data_type_for_boolean in InvalidDataTypes.for_booleans:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_boolean,
                expected_error_message=f"{field_location} must be a boolean",
            )

    @staticmethod
    def test_positive_integer_value(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_positive_integers_to_test: list,
        max_value: int = None,
    ):
        """
        Test that a FHIR model accepts valid positive integer values and rejects the following
        invalid values:
        * All invalid data types
        * Non-postive integers
        * If there is a max value: a value which exceeds the maximum
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(
            test_instance,
            valid_json_data,
            field_location,
            valid_positive_integers_to_test,
        )

        # Test invalid data types
        for invalid_data_type_for_integer in InvalidDataTypes.for_integers:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_integer,
                expected_error_message=f"{field_location} must be a positive integer",
            )

        # Test non-positive integers
        for non_positive_integer in [-10, -1, 0]:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=non_positive_integer,
                expected_error_message=f"{field_location} must be a positive integer",
            )

        # Test value exceeding the max value (if applicable)
        if max_value:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=max_value + 1,
                expected_error_message=f"{field_location} must be an integer in the range 1 to " + f"{str(max_value)}",
            )

    @staticmethod
    def test_decimal_or_integer_value(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_decimals_and_integers_to_test: list,
    ):
        """
        Test that a FHIR model accepts valid decimal or integer values and rejects the following
        invalid values:
        * All invalid data types
        * If there is a max number of decimal places: a Decimal with too many decimal places
        """

        valid_json_data = deepcopy(test_instance.json_data)

        # Test that valid data is accepted
        test_valid_values_accepted(
            test_instance,
            valid_json_data,
            field_location,
            valid_decimals_and_integers_to_test,
        )

        # Test invalid data types
        for invalid_data_type_for_decimals_or_integers in InvalidDataTypes.for_decimals_or_integers:
            test_invalid_values_rejected(
                test_instance,
                valid_json_data,
                field_location=field_location,
                invalid_value=invalid_data_type_for_decimals_or_integers,
                expected_error_message=f"{field_location} must be a number",
            )

    @staticmethod
    def test_valid_combinations_of_contained_and_performer_accepted(
        test_instance: unittest.TestCase,
        contained: list,
        performer: dict,
    ):
        """
        Takes a valid combination of contained and performer objects and ensures that no
        validation error is raised
        """
        valid_json_data = deepcopy(test_instance.json_data)
        valid_json_data = parse("contained").update(valid_json_data, contained)
        valid_json_data = parse("performer").update(valid_json_data, performer)

        test_instance.assertIsNone(test_instance.validator.validate(valid_json_data))

    @staticmethod
    def test_invalid_performer_actor_reference_rejected(
        test_instance: unittest.TestCase,
        contained: list,
        performer: dict,
        expected_error_message: str,
    ):
        """
        Takes a combination of contained and performer object which is invalid due to
        either contained Practitioner ID, performer.actor.reference, or a combination of
        the two, and checks that the appropriate error is raised
        """
        invalid_json_data = deepcopy(test_instance.json_data)
        invalid_json_data = parse("contained").update(invalid_json_data, contained)

        invalid_json_data = parse("performer").update(invalid_json_data, performer)

        with test_instance.assertRaises(ValueError) as error:
            test_instance.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        test_instance.assertIn(expected_error_message, actual_error_messages)

    @staticmethod
    def test_valid_combinations_of_contained_and_patient_accepted(
        test_instance: unittest.TestCase,
        contained: list,
        patient: dict,
    ):
        """
        Takes a valid combination of contained and patient objects and ensures that no
        validation error is raised
        """
        valid_json_data = deepcopy(test_instance.json_data)
        valid_json_data = parse("contained").update(valid_json_data, contained)
        valid_json_data = parse("patient").update(valid_json_data, patient)

        test_instance.assertIsNone(test_instance.validator.validate(valid_json_data))

    @staticmethod
    def test_invalid_patient_reference_rejected(
        test_instance: unittest.TestCase,
        contained: list,
        patient: dict,
        expected_error_message: str,
    ):
        """
        Takes a combination of contained and patient object which is invalid due to
        either contained Patient ID, patient.reference, or a combination of
        the two, and checks that the appropriate error is raised
        """
        invalid_json_data = deepcopy(test_instance.json_data)
        invalid_json_data = parse("contained").update(invalid_json_data, contained)

        invalid_json_data = parse("patient").update(invalid_json_data, patient)

        with test_instance.assertRaises(ValueError) as error:
            test_instance.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        test_instance.assertIn(expected_error_message, actual_error_messages)
