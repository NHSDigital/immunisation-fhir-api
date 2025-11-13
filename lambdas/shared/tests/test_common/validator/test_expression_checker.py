import unittest

from common.validator.error_report.record_error import ErrorReport
from common.validator.expression_checker import ExpressionChecker


class MockParser:
    """Minimal parser providing get_key_value for ONLYIF tests."""

    def __init__(self, data=None):
        self._data = data or {}

    def get_key_value(self, field_name):
        return [self._data.get(field_name, "")]


class TestExpressionChecker(unittest.TestCase):
    """Unit tests limited to expression types used in the provided schema."""

    def make_checker(self, mock_data=None, summarise=False, report=True):
        return ExpressionChecker(MockParser(mock_data), summarise, report)

    # STRING
    def test_string_valid_and_invalid(self):
        checker = self.make_checker()
        # Valid NHS number length
        self.assertIsNone(
            checker.validate_expression(
                "STRING",
                "NHS_NUMBER",
                "contained|#:Patient|identifier|#:https://fhir.nhs.uk/Id/nhs-number|value",
                "9876543210",
            )
        )
        # Empty should fail NHS number string rule
        self.assertIsInstance(
            checker.validate_expression(
                "STRING", "NHS_NUMBER", "contained|#:Patient|identifier|#:https://fhir.nhs.uk/Id/nhs-number|value", ""
            ),
            ErrorReport,
        )

    # LIST
    def test_list_valid_and_invalid(self):
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("LIST", "PERSON_NAME", "PERSON_NAME", ["Alice"]))
        self.assertIsInstance(checker.validate_expression("LIST", "PERSON_NAME", "PERSON_NAME", []), ErrorReport)
        self.assertIsInstance(checker.validate_expression("LIST", "", "PERSON_NAME", "Alice"), ErrorReport)

    # DATE
    def test_date_valid_and_invalid(self):
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("DATE", "", "date_field", "2025-01-01"))
        self.assertIsInstance(checker.validate_expression("DATE", "", "date_field", "2025-13-01"), ErrorReport)


#     # DATETIME
#     def test_datetime_valid_and_invalid(self):
#         checker = self.make_checker()
#         # Full date only allowed
#         self.assertIsNone(checker.validate_expression("DATETIME", "", "dt_field", "2025-01-01", 1))
#         # Bad format should raise
#         with self.assertRaises(Exception):
#             checker.validate_expression("DATETIME", "", "dt_field", "2025-01-01T10:00:00Z", 1)


#     # BOOLEAN
#     def test_boolean_valid_and_invalid(self):
#         checker = self.make_checker()
#         self.assertIsNone(checker.validate_expression("BOOLEAN", "", "bool_field", True, 1))
#         self.assertIsInstance(checker.validate_expression("BOOLEAN", "", "bool_field", "true", 1), ErrorReport)

#     # POSITIVEINTEGER
#     def test_positive_integer_valid_and_invalid(self):
#         checker = self.make_checker()
#         self.assertIsNone(checker.validate_expression("POSITIVEINTEGER", "", "pos_field", "2", 1))
#         self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", "pos_field", "0", 1), ErrorReport)
#         self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", "pos_field", "-5", 1), ErrorReport)
#         self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", "pos_field", "abc", 1), ErrorReport)

#     # INTDECIMAL
#     def test_intdecimal_valid_and_invalid(self):
#         checker = self.make_checker()
#         self.assertIsNone(checker.validate_expression("INTDECIMAL", "", "num_field", "1.23", 1))
#         self.assertIsNone(checker.validate_expression("INTDECIMAL", "", "num_field", 3, 1))
#         self.assertIsInstance(checker.validate_expression("INTDECIMAL", "", "num_field", "abc", 1), ErrorReport)


# class DummyParserEx:
#     def __init__(self, data=None, raise_on_get=False):
#         self._data = data or {}
#         self._raise_on_get = raise_on_get

#     def get_key_value(self, field_name):
#         if self._raise_on_get:
#             raise RuntimeError("boom")
#         return [self._data.get(field_name, "")]


if __name__ == "__main__":
    unittest.main()
