"""Unit tests for batch utils"""

import unittest
from unittest.mock import patch
from decimal import Decimal
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import Urls
    from utils_for_fhir_conversion import _is_not_empty, Generate, Add, Convert


class TestBatchUtils(unittest.TestCase):
    """Tests for the generic batch utils"""

    def setUp(self):
        self.fields_dict = {"key1": "value1", "key2": None, "key3": False, "key4": ""}
        self.fields_dict_non_empty = {"key1": "value1", "key3": False}

    def test_is_not_empty(self):
        "Test that _is_not_empty returns a boolean to indicate if a value is not empty"
        for non_empty_value in [False, "Hello", 0, 0.0, {"Key": ""}, ["Hello"]]:
            self.assertTrue(_is_not_empty(non_empty_value))

        for empty_value in [None, "", [], {}, (), [""]]:
            self.assertFalse(_is_not_empty(empty_value))


class TestBatchUtilsConvert(unittest.TestCase):
    """Tests for the batch utils Convert functions"""

    def test_convert_date_time(self):
        """
        Tests that _convert_date_time returns a FHIR formatted date_time when a acceptably formatted date_time is
        received, or returns the original value if this is not possible
        """
        # Valid date_times
        for value, expected in [
            ("20000101T111111", "2000-01-01T11:11:11+00:00"),  # Without timezone
            ("20000101T11111100", "2000-01-01T11:11:11+00:00"),  # UTC
            ("20000101T11111101", "2000-01-01T11:11:11+01:00"),  # BST
        ]:
            self.assertEqual(Convert.date_time(value), expected)

        # Invalid date_times
        for value in [
            "20000101T11:11:11",  # Semi colons in time
            "20000101T1111110000",  # Timezone given as 4 digits
            "20000101T111111+00",  # + Timezone
            "20000101T111111-01",  # - Timezone
            "20000101T11111102",  # Timezone not accepted
        ]:
            self.assertEqual(Convert.date_time(value), value)

    def test_convert_date(self):
        """Tests that _covert_date returns a FHIR formatted date when a acceptably formatted date is
        received, or returns the original value if this is not possible"""
        # Valid_dates
        self.assertEqual(Convert.date("20000101"), "2000-01-01")
        self.assertEqual(Convert.date("19821115"), "1982-11-15")

        # Invalid_dates
        for value in [
            "2000-01-01",
            20000101,
            "20000230",
            "2000011",
            "990101",
            "20000101T00:00",
        ]:
            self.assertEqual(Convert.date(value), value)

    def test_convert_gender_code(self):
        """
        Tests that _convert_gender_code returns the FHIR-mapped gender if the code is recognised, or returns
        the original value if this is not possible
        """
        # Valid gender codes
        for code, expected in [
            ("1", "male"),
            ("2", "female"),
            ("9", "other"),
            ("0", "unknown"),
        ]:
            self.assertEqual(Convert.gender_code(code), expected)

        # Invalid gender codes
        for value in [1, "invalid", None]:
            self.assertEqual(Convert.gender_code(value), value)

    def test_convert_boolean(self):
        """
        Tests that _convert_boolean returns the corresponding python boolean where the value is a string
        represenetation of a boolean, or returns the original value if it is not a string representation of a boolean.
        """
        for value in ["true", "TRUE", "True"]:
            self.assertEqual(Convert.boolean(value), True)

        for value in ["false", "FALSE", "FaLsE"]:
            self.assertEqual(Convert.boolean(value), False)

        for value in [1, "invalid", None]:
            self.assertEqual(Convert.boolean(value), value)

    def test_convert_integer_or_decimal(self):
        """
        Tests that _convert_integer_or_decimal returns the corresponding integer where the value is a string
        representation of an integer, the corresponding Decimal where the value is a string representation of
        a decimal, or the original value if it is not a string representation of either an integer or a decimal.
        """
        # Integers
        for value, expected in [("1", 1), ("-1", -1), ("234", 234)]:
            self.assertEqual(Convert.integer_or_decimal(value), expected)
            assert isinstance(Convert.integer_or_decimal(value), int)

        # Decimals
        for value, expected in [("1.1", Decimal("1.1")), ("-1.73", Decimal("-1.73"))]:
            self.assertEqual(Convert.integer_or_decimal(value), expected)
            assert isinstance(Convert.integer_or_decimal(value), Decimal)

        # Invalid decimal/ integer
        for value in [["1.2"], "invalid", "12notanumber", None]:
            self.assertEqual(Convert.integer_or_decimal(value), value)

    def test_convert_integer(self):
        """
        Tests that _convert_integer returns the corresponding integer where the value is a string
        representation of an integer, or otherwise returns the original value
        """
        self.assertEqual(Convert.integer("1"), 1)
        self.assertEqual(Convert.integer(1), 1)
        self.assertEqual(Convert.integer("0"), 0)
        self.assertEqual(Convert.integer("234"), 234)

        for value in ["1.2", ["1"], "invalid", None]:
            self.assertEqual(Convert.integer(value), value)

    def test_convert_to_lower(self):
        """
        Tests that _convert_to_lower returns a lowercase string if the value is a string, or otherwise
        returns the original value.
        """
        for code, expected in [
            ("1", "1"),
            ("TEST1", "test1"),
            ("test2", "test2"),
            ("teST3", "test3"),
            (["TEST4"], ["TEST4"]),
            (1, 1),
            (None, None),
        ]:
            self.assertEqual(Convert.to_lower(code), expected)


class TestBatchUtilsCreate(unittest.TestCase):
    """Tests for the batch utils Create functions"""

    def test_create_dictionary(self):
        """
        Tests that _create_dictionary returns the inputted dictionary, with key-value pairs removed where
        the value is empty.
        """
        input_dict = {"key1": "value1", "key2": None, "key3": False, "key4": ""}
        expected_output = {"key1": "value1", "key3": False}
        self.assertEqual(Generate.dictionary(input_dict), expected_output)

    def test_create_extension_item(self):
        """
        Tests that _create_extension_item returns an appropriately formatted extension item,
        containing only key-value pairs where the value is non-empty.
        """
        # All values non-empty
        actual = Generate.extension_item("testUrl", "testSystem", "ABC", "testDisplay")
        expected = {
            "url": "testUrl",
            "valueCodeableConcept": {
                "coding": [
                    {"system": "testSystem", "code": "ABC", "display": "testDisplay"}
                ]
            },
        }
        self.assertEqual(expected, actual)

        # Only display non-empty
        actual = Generate.extension_item("testUrl", "testSystem", None, "testDisplay")
        expected = {
            "url": "testUrl",
            "valueCodeableConcept": {
                "coding": [{"system": "testSystem", "display": "testDisplay"}]
            },
        }
        self.assertEqual(expected, actual)

        # Only code non-empty
        actual = Generate.extension_item("testUrl", "testSystem", "ABC", "")
        expected = {
            "url": "testUrl",
            "valueCodeableConcept": {
                "coding": [{"system": "testSystem", "code": "ABC"}]
            },
        }
        self.assertEqual(expected, actual)


class TestBatchUtilsAdd(unittest.TestCase):
    """Tests for the batch utils Add functions"""

    def setUp(self):
        self.test_dict_some_empty = {
            "key1": "value1",
            "key2": None,
            "key3": False,
            "key4": "",
        }
        self.test_dict_none_empty = {"key1": "value1", "key3": False}
        self.test_dict_empty = {"key5": "", "key6": None, "key7": []}

    def test_add_item(self):
        """Tests that _add_item adds a key-value pair to a dictionary if and only if the value is non-empty."""
        test_dict = {}

        # Test non-empty value
        Add.item(test_dict, "key1", "value1")
        self.assertEqual({"key1": "value1"}, test_dict)

        # Test empty value
        Add.item(test_dict, "key2", [])
        self.assertEqual({"key1": "value1"}, test_dict)

        # Test with conversion function
        Add.item(test_dict, "key2", "1", Convert.gender_code)
        self.assertEqual(test_dict, {"key1": "value1", "key2": "male"})

    def test_add_dictionary(self):
        """
        Tests that _add_dictionary adds a key-value pair to a dictionary, where the value is a dictionary
        with key-value pairs removed if the value is empty.
        """
        test_dict = {}

        # Test dict with some empty items
        Add.dictionary(test_dict, "test1", self.test_dict_some_empty)
        self.assertEqual(test_dict, {"test1": self.test_dict_none_empty})

        # Test dict with all empty items
        Add.dictionary(test_dict, "test1", self.test_dict_empty)
        self.assertEqual(test_dict, {"test1": self.test_dict_none_empty})

    def test_add_list_of_dictionary(self):
        """
        Tests that _add_list_of_dictionary adds a key-value pair to a dictionary, where the value is a list
        containing a single item which is a dictionary with key-value pairs removed if the value is empty.
        """
        test_dict = {}

        # Test dict with some empty items
        Add.list_of_dict(test_dict, "test1", self.test_dict_some_empty)
        self.assertEqual(test_dict, {"test1": [self.test_dict_none_empty]})

        # Test dict with all empty items
        Add.list_of_dict(test_dict, "test1", self.test_dict_empty)
        self.assertEqual(test_dict, {"test1": [self.test_dict_none_empty]})

    def test_add_custom_item(self):
        """
        Tests that _add_custom_item adds a key-value pair to a dictionary, where the value is a custom item,
        if and only if at least one of the listed values is non-empty.
        """
        test_dict = {}

        # Test list with some empty items
        Add.custom_item(
            test_dict, "test1", ["", "test1", None], [{"test1": ["testValue"]}]
        )
        self.assertEqual(test_dict, {"test1": [{"test1": ["testValue"]}]})

        # Test list with all empty items
        Add.custom_item(test_dict, "test2", ["", None], "value2")
        self.assertEqual(test_dict, {"test1": [{"test1": ["testValue"]}]})

    def test_add_snomed(self):
        """
        Tests that _add_snomed adds a key-value pair to a dictionary, where the value is a dictionary with any
        key-value pairs removed where the value is non-empty, if and only if at least one of the values is non-empty.
        """
        # Code and display non-empty
        test_dict = {}
        Add.snomed(test_dict, "test1", "ABC", "testDisplay")
        expected = {
            "test1": {
                "coding": [
                    {"system": Urls.SNOMED, "code": "ABC", "display": "testDisplay"}
                ]
            }
        }
        self.assertEqual(test_dict, expected)

        # Code empty and display non-empty
        test_dict = {}
        Add.snomed(test_dict, "test2", "", "testDisplay")
        expected = {
            "test2": {"coding": [{"system": Urls.SNOMED, "display": "testDisplay"}]}
        }
        self.assertEqual(test_dict, expected)

        # Code non-empty and display empty
        test_dict = {}
        Add.snomed(test_dict, "test3", "ABC", "")
        expected = {"test3": {"coding": [{"system": Urls.SNOMED, "code": "ABC"}]}}
        self.assertEqual(test_dict, expected)

        # Code and display empty
        test_dict = {}
        Add.snomed(test_dict, "test3", "", "")
        self.assertEqual(test_dict, {})
