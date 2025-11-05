import unittest
from unittest.mock import MagicMock, patch

from common.validator.constants.enums import ExceptionLevels
from common.validator.expression_checker import ExpressionChecker
from common.validator.record_error import ErrorReport


class MockParser(unittest.TestCase):
    """
    Mock parser used to simulate field value lookups
    for ExpressionChecker during testing.
    """

    def __init__(self, data=None):
        self._data = data or {}

    def get_key_value(self, field_name):
        """Return a list to mimic parser contract."""
        return [self._data.get(field_name, "")]


class TestExpressionChecker(unittest.TestCase):
    """
    Unit tests for ExpressionChecker validation logic.
    Each test validates a specific expression rule type.
    """

    def make_checker(self, mock_data=None, summarise=False, report=True):
        """Helper to create an ExpressionChecker with mock parser data."""
        return ExpressionChecker(MockParser(mock_data), summarise, report)

    # Date Time Check
    def test_datetime_valid(self):
        """Valid ISO date should pass without error."""
        checker = self.make_checker({"date_field": "2025-01-01"})
        error = checker.validate_expression("DATETIME", None, "date_field", "2025-01-01", 1)
        self.assertIsNone(error)

    def test_datetime_unexpected_exception(self):
        """Passing incompatible type should raise an error report."""
        checker = self.make_checker()
        error = checker.validate_expression("DATETIME", None, "date_field", object(), 1)
        self.assertIsInstance(error, ErrorReport)

    def test_uuid_valid_and_invalid(self):
        """UUID validation should pass for valid UUIDs and fail for invalid ones."""
        checker = self.make_checker()
        valid_uuid = "12345678-1234-5678-1234-567812345678"
        self.assertIsNone(checker.validate_expression("UUID", None, "uuid_field", valid_uuid, 1))
        self.assertIsInstance(checker.validate_expression("UUID", None, "uuid_field", "not-a-uuid", 1), ErrorReport)

    # Numeric Length and Regex
    def test_integer_length_and_regex_rules(self):
        """Test integer, length, and regex-based validations."""
        checker = self.make_checker()

        # INT should pass with numeric value
        self.assertIsNone(checker.validate_expression("INT", None, "int_field", "42", 1))

        # LENGTH too long -> Error
        self.assertIsInstance(checker.validate_expression("LENGTH", "3", "str_field", "abcd", 1), ErrorReport)

        # REGEX mismatch -> Error
        self.assertIsInstance(checker.validate_expression("REGEX", r"^abc$", "regex_field", "abcd", 1), ErrorReport)

    # Case & String Position Rules
    def test_upper_lower_startswith_endswith_rules(self):
        """Validate case and string boundary conditions."""
        checker = self.make_checker()

        # UPPER
        self.assertIsNone(checker.validate_expression("UPPER", None, "upper_field", "ABC", 1))
        self.assertIsInstance(checker.validate_expression("UPPER", None, "upper_field", "AbC", 1), ErrorReport)

        # LOWER
        self.assertIsNone(checker.validate_expression("LOWER", None, "lower_field", "abc", 1))
        self.assertIsInstance(checker.validate_expression("LOWER", None, "lower_field", "abC", 1), ErrorReport)

        # STARTSWITH
        self.assertIsNone(checker.validate_expression("STARTSWITH", "ab", "start_field", "abc", 1))
        self.assertIsInstance(checker.validate_expression("STARTSWITH", "zz", "start_field", "abc", 1), ErrorReport)

        # ENDSWITH
        self.assertIsNone(checker.validate_expression("ENDSWITH", "bc", "end_field", "abc", 1))
        self.assertIsInstance(checker.validate_expression("ENDSWITH", "zz", "end_field", "abc", 1), ErrorReport)

    # --- EMPTY & NOTEMPTY ------------------------------------------------

    def test_empty_and_notempty_rules(self):
        """Validate checks for empty and non-empty fields."""
        checker = self.make_checker()

        # EMPTY
        self.assertIsNone(checker.validate_expression("EMPTY", None, "empty_field", "", 1))
        self.assertIsInstance(checker.validate_expression("EMPTY", None, "empty_field", "value", 1), ErrorReport)

        # NOTEMPTY
        self.assertIsNone(checker.validate_expression("NOTEMPTY", None, "notempty_field", "value", 1))
        self.assertIsInstance(checker.validate_expression("NOTEMPTY", None, "notempty_field", "", 1), ErrorReport)

    # --- NUMERIC RANGES --------------------------------------------------

    def test_positive_and_nrange_rules(self):
        """Check positive and numeric range validations."""
        checker = self.make_checker()

        # POSITIVE
        self.assertIsNone(checker.validate_expression("POSITIVE", None, "positive_field", "1.2", 1))
        self.assertIsInstance(checker.validate_expression("POSITIVE", None, "positive_field", "-3", 1), ErrorReport)

        # NRANGE
        self.assertIsNone(checker.validate_expression("NRANGE", "1,10", "range_field", "5", 1))
        self.assertIsInstance(checker.validate_expression("NRANGE", "a,b", "range_field", "5", 1), ErrorReport)

    # --- COMPARISONS & LIST MEMBERSHIP -----------------------------------

    def test_inarray_equal_notequal_rules(self):
        """Test INARRAY, EQUAL, and NOTEQUAL expressions."""
        checker = self.make_checker()

        # INARRAY
        self.assertIsNone(checker.validate_expression("INARRAY", "a,b", "array_field", "a", 1))
        self.assertIsInstance(checker.validate_expression("INARRAY", "a,b", "array_field", "z", 1), ErrorReport)

        # EQUAL
        self.assertIsNone(checker.validate_expression("EQUAL", "x", "equal_field", "x", 1))
        self.assertIsInstance(checker.validate_expression("EQUAL", "x", "equal_field", "y", 1), ErrorReport)

        # NOTEQUAL
        self.assertIsNone(checker.validate_expression("NOTEQUAL", "x", "notequal_field", "y", 1))
        self.assertIsInstance(checker.validate_expression("NOTEQUAL", "x", "notequal_field", "x", 1), ErrorReport)

    # --- DOMAIN-SPECIFIC RULES -------------------------------------------

    def test_postcode_gender_nhsnumber_rules(self):
        """Check NHS number, gender, and postcode validations."""
        checker = self.make_checker()

        # NHSNUMBER invalid
        self.assertIsInstance(checker.validate_expression("NHSNUMBER", None, "nhs_field", "123", 1), ErrorReport)

        # GENDER
        self.assertIsNone(checker.validate_expression("GENDER", None, "gender_field", "0", 1))
        self.assertIsInstance(checker.validate_expression("GENDER", None, "gender_field", "x", 1), ErrorReport)

        # POSTCODE
        self.assertIsInstance(checker.validate_expression("POSTCODE", None, "postcode_field", "XYZ", 1), ErrorReport)

    # --- COLLECTION SIZE RULES -------------------------------------------

    def test_maxobjects_rule(self):
        """MAXOBJECTS validates maximum allowed length of list-like fields."""
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("MAXOBJECTS", "1", "list_field", [], 1))
        self.assertIsInstance(checker.validate_expression("MAXOBJECTS", "1", "list_field", [1, 2], 1), ErrorReport)

    # --- LOOKUP & CONDITIONAL RULES --------------------------------------

    def test_lookup_and_keycheck_rules(self):
        """Force unexpected or missing lookup paths."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("LOOKUP", None, "lookup_field", "unknown", 1), ErrorReport)

    def test_onlyif_uses_parser_values(self):
        """ONLYIF uses parser to conditionally validate based on another field."""
        mock_data = {"location_field": "VAL"}
        checker = self.make_checker(mock_data)

        # expressionRule format: field|expected_value
        result_match = checker.validate_expression("ONLYIF", "location_field|VAL", "test_field", "any", 1)
        result_mismatch = checker.validate_expression("ONLYIF", "location_field|NOPE", "test_field", "any", 1)

        self.assertIsNone(result_match)
        self.assertIsInstance(result_mismatch, ErrorReport)


class TestExpressionLookUp(unittest.TestCase):
    def setUp(self):
        self.MockLookUpData = patch("common.validator.expression_checker.LookUpData").start()
        self.MockKeyData = patch("common.validator.expression_checker.KeyData").start()

        self.mock_summarise = MagicMock()
        self.mock_report_exception = MagicMock()
        self.mock_data_parser = MagicMock()

        self.expression_checker = ExpressionChecker(
            self.mock_data_parser, self.mock_summarise, self.mock_report_exception
        )

    def tearDown(self):
        patch.stopall()

    def test_validate_datetime_valid(self):
        result = self.expression_checker.validate_expression(
            "DATETIME", expression_rule="", field_name="timestamp", field_value="2022-01-01T12:00:00", row={}
        )
        self.assertEqual(
            result.message,
            "Unexpected exception [ValueError]: Invalid isoformat string: '2022-01-01T12:00:00'",
        )
        self.assertEqual(result.code, ExceptionLevels.UNEXPECTED_EXCEPTION)
        self.assertEqual(result.field, "timestamp")

    def test_validate_uuid_valid(self):
        result = self.expression_checker.validate_expression(
            "UUID", expression_rule="", field_name="id", field_value="550e8400-e29b-41d4-a716-446655440000", row={}
        )
        self.assertTrue(result is None)

    def test_validate_integer_invalid(self):
        result = self.expression_checker.validate_expression(
            "INT", expression_rule="", field_name="age", field_value="hello world", row={}
        )
        self.assertEqual(result.code, ExceptionLevels.UNEXPECTED_EXCEPTION)
        self.assertEqual(result.field, "age")
        self.assertIn("invalid literal for int()", result.message)

    def test_validate_in_array(self):
        # Mock data_parser.get_key_values
        self.mock_data_parser.get_key_values.return_value = ["val1", "val2"]

        result = self.expression_checker.validate_expression(
            "INARRAY", expression_rule="", field_name="some_field", field_value="val2", row={}
        )
        self.assertEqual(result.message, "Value not in array check failed")
        self.assertEqual(result.field, "some_field")

    def test_validate_expression_type_not_found(self):
        result = self.expression_checker.validate_expression(
            "UNKNOWN", expression_rule="", field_name="field", field_value="value", row={}
        )
        self.assertIn("Schema expression not found", result)


class DummyParserEx:
    """A dummy parser that optionally raises exceptions when fetching values."""

    def __init__(self, data=None, raise_on_get=False):
        self._data = data or {}
        self._raise_on_get = raise_on_get

    def get_key_value(self, field_name):
        """Simulate field lookup, optionally raising an error."""
        if self._raise_on_get:
            raise RuntimeError("boom")
        return [self._data.get(field_name, "")]


class StubLookup:
    """Stub object to simulate lookup behavior with optional exception raising."""

    def __init__(self, raise_on_call=False):
        self._raise_on_call = raise_on_call

    def find_lookup(self, value):
        if self._raise_on_call:
            raise RuntimeError("boom")
        return ""  # always empty to force error path


class StubKeyData:
    """Stub for key data operations with optional exception raising."""

    def __init__(self, raise_on_call=False):
        self._raise_on_call = raise_on_call

    def findKey(self, key_source, field_value):
        if self._raise_on_call:
            raise RuntimeError("boom")
        return False  # always fail to trigger error branch


class TestExpressionCheckerExceptions(unittest.TestCase):
    """
    Tests edge cases and exception-handling paths in ExpressionChecker.
    Focuses on behavior when report=True vs report=False.
    """

    def make_checker(self, data=None, report=True, raise_on_get=False):
        """Helper to construct ExpressionChecker with dummy parser."""
        return ExpressionChecker(DummyParserEx(data, raise_on_get), False, report)

    # --- REGEX, IN, LENGTH, FLOAT, UUID ----------------------------------

    def test_regex_unexpected_true_false(self):
        """REGEX should return ErrorReport when report=True, None when report=False."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("REGEX", None, "regex_field", "abc", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("REGEX", None, "regex_field", "abc", 1))

    def test_in_unexpected_true_false(self):
        """IN should trigger error when report=True and pass silently when report=False."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("IN", "ab", "in_field", None, 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("IN", "ab", "in_field", None, 1))

    def test_length_unexpected_true_false(self):
        """LENGTH rule with invalid argument should trigger exception path."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("LENGTH", "x", "length_field", "abcd", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("LENGTH", "x", "length_field", "abcd", 1))

    def test_float_unexpected_true_false(self):
        """FLOAT rule should fail when value cannot be parsed as float."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("FLOAT", None, "float_field", "abc", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("FLOAT", None, "float_field", "abc", 1))

    def test_uuid_unexpected_true_false(self):
        """UUID rule should handle malformed UUIDs properly."""
        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("UUID", None, "uuid_field", "not-a-uuid", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("UUID", None, "uuid_field", "not-a-uuid", 1))

    # --- MAXOBJECTS ------------------------------------------------------

    def test_maxobjects_unexpected_true_false(self):
        """MAXOBJECTS should handle non-iterable input gracefully."""

        class NoLen:
            """Dummy object without __len__."""

            pass

        checker = self.make_checker(report=True)
        self.assertIsInstance(checker.validate_expression("MAXOBJECTS", "1", "max_field", NoLen(), 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        self.assertIsNone(checker_no_report.validate_expression("MAXOBJECTS", "1", "max_field", NoLen(), 1))

    # --- ONLYIF ----------------------------------------------------------

    def test_onlyif_unexpected_true_false(self):
        """ONLYIF rule should handle parser errors based on report flag."""
        checker = self.make_checker(report=True, raise_on_get=True)
        self.assertIsInstance(checker.validate_expression("ONLYIF", "loc|VAL", "field", "x", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False, raise_on_get=True)
        self.assertIsNone(checker_no_report.validate_expression("ONLYIF", "loc|VAL", "field", "x", 1))

    # --- LOOKUP & KEYCHECK -----------------------------------------------

    def test_lookup_unexpected_true_false(self):
        """LOOKUP rule should handle raised exceptions gracefully."""
        checker = self.make_checker(report=True)
        checker.data_look_up = StubLookup(raise_on_call=True)
        self.assertIsInstance(checker.validate_expression("LOOKUP", None, "lookup_field", "x", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        checker_no_report.data_look_up = StubLookup(raise_on_call=True)
        self.assertIsNone(checker_no_report.validate_expression("LOOKUP", None, "lookup_field", "x", 1))

    def test_keycheck_unexpected_true_false(self):
        """KEYCHECK rule should handle raised exceptions gracefully."""
        checker = self.make_checker(report=True)
        checker.key_data = StubKeyData(raise_on_call=True)
        self.assertIsInstance(checker.validate_expression("KEYCHECK", "Site", "key_field", "val", 1), ErrorReport)

        checker_no_report = self.make_checker(report=False)
        checker_no_report.key_data = StubKeyData(raise_on_call=True)
        self.assertIsNone(checker_no_report.validate_expression("KEYCHECK", "Site", "key_field", "val", 1))

    # --- DATE & STRING EDGE CASES ---------------------------------------

    def test_date_alias_and_upper_lower_edges(self):
        """DATE alias should behave like DATETIME; string rules should handle None gracefully."""
        checker = self.make_checker({"date_field": "2025-01-01"})
        self.assertIsNone(checker.validate_expression("DATE", None, "date_field", "2025-01-01", 1))

        checker_none = self.make_checker()
        self.assertIsInstance(checker_none.validate_expression("UPPER", None, "upper_field", None, 1), ErrorReport)
        self.assertIsInstance(checker_none.validate_expression("LOWER", None, "lower_field", None, 1), ErrorReport)
        self.assertIsInstance(checker_none.validate_expression("STARTSWITH", "a", "start_field", None, 1), ErrorReport)
        self.assertIsInstance(checker_none.validate_expression("ENDSWITH", "a", "end_field", None, 1), ErrorReport)

    # --- NUMERIC RANGE ---------------------------------------------------

    def test_nrange_out_of_range(self):
        """NRANGE rule should return error when value exceeds upper bound."""
        checker = self.make_checker()
        self.assertIsInstance(checker.validate_expression("NRANGE", "1,10", "range_field", "11", 1), ErrorReport)

    # --- DOMAIN-SPECIFIC -------------------------------------------------

    def test_postcode_valid_and_unexpected(self):
        """POSTCODE should pass for valid UK postcode and fail otherwise."""
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("POSTCODE", None, "postcode_field", "EC1A 1BB", 1))
        self.assertIsInstance(checker.validate_expression("POSTCODE", None, "postcode_field", None, 1), ErrorReport)

    def test_nhsnumber_valid_and_unexpected(self):
        """NHSNUMBER should pass for valid NHS number format and fail otherwise."""
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("NHSNUMBER", None, "nhs_field", "61234567890", 1))
        self.assertIsInstance(checker.validate_expression("NHSNUMBER", None, "nhs_field", None, 1), ErrorReport)

    # --- IN RULE NORMAL PATHS -------------------------------------------

    def test_in_pass_fail(self):
        """IN rule should detect substring presence correctly."""
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("IN", "ab", "in_field", "zzabzz", 1))
        self.assertIsInstance(checker.validate_expression("IN", "ab", "in_field", "zz", 1), ErrorReport)


if __name__ == "__main__":
    unittest.main()
