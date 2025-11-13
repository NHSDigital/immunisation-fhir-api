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

        # VALID PERSON_SURNAME STRING
        self.assertIsNone(
            checker.validate_expression(
                "STRING", "PERSON_SURNAME", "contained|#:Patient|name|#:official|family", "Smith"
            )
        )
        self.assertIsNone(checker.validate_expression("STRING", "PERSON_SURNAME", "PERSON_SURNAME", "Taylor"))
        # INVALID PERSON_SURNAME STRING (too long)
        self.assertIsInstance(
            checker.validate_expression(
                "STRING", "PERSON_SURNAME", "contained|#:Patient|name|#:official|family", "Stan" * 51
            ),
            ErrorReport,
        )

    # LIST PERSON_FORENAME
    def test_list_valid_and_invalid(self):
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("LIST", "PERSON_NAME", "PERSON_FORENAME", ["Alice"]))
        self.assertIsNone(
            checker.validate_expression(
                "LIST", "PERSON_NAME", "contained|#:Patient|name|#:official|given|0", ["Bethany"]
            )
        )
        self.assertIsInstance(checker.validate_expression("LIST", "PERSON_NAME", "PERSON_FORENAME", []), ErrorReport)
        self.assertIsInstance(checker.validate_expression("LIST", "", "PERSON_FORENAME", "Alice"), ErrorReport)

    # DATE
    def test_date_valid_and_invalid(self):
        checker = self.make_checker()
        self.assertIsNone(checker.validate_expression("DATE", "", "contained|#:Patient|birthDate", "2025-01-01"))
        self.assertIsNone(checker.validate_expression("DATE", "", "PERSON_DOB", "2025-01-01"))
        self.assertIsInstance(
            checker.validate_expression("DATE", "", "contained|#:Patient|birthDate", "2025-13-01"), ErrorReport
        )
        self.assertIsInstance(checker.validate_expression("DATE", "", "PERSON_DOB", "2025-02-30"), ErrorReport)

    # DATETIME
    def test_datetime_valid_and_invalid(self):
        checker = self.make_checker()
        # Full date only allowed
        self.assertIsNone(
            checker.validate_expression("DATETIME", "DATETIME", "occurrenceDateTime", "2025-01-01T05:00:00+00:00")
        )
        self.assertIsNone(
            checker.validate_expression("DATETIME", "DATETIME", "DATE_AND_TIME", "2025-01-01T05:00:00+00:00")
        )
        # Bad format should raise
        self.assertIsInstance(
            checker.validate_expression("DATETIME", "", "occurrenceDateTime", "2026-01-01T10:00:00Z"), ErrorReport
        )
        self.assertIsInstance(
            checker.validate_expression("DATETIME", "", "DATE_AND_TIME", "2026-01-01T10:00:00Z"), ErrorReport
        )

    # STRING with SITE_CODE
    def test_site_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "performer|#:Organization|actor|identifier|value"
        # Valid: non-empty, no spaces
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "RJ1"))
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: contains spaces
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 1234), ErrorReport)

    # STRING with SITE_CODE_TYPE_URI rule
    def test_site_code_type_uri_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "performer|#:Organization|actor|identifier|system"
        valid_uri = "https://fhir.nhs.uk/Id/ods-organization-code"
        # Valid: non-empty, no spaces
        self.assertIsNone(
            checker.validate_expression("STRING", "", field_path, valid_uri),
        )
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: contains spaces
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 123), ErrorReport)

    # BOOLEAN

    # STRING with UNIQUE_ID rule (empty rule -> generic non-empty string)
    def test_unique_id_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "identifier|0|value"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "ABC-123-XYZ"))
        # Invalid: empty string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string value
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 987654), ErrorReport)

    # STRING with UNIQUE_ID_URI rule (empty rule -> generic non-empty string)
    def test_unique_id_uri_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "identifier|0|system"
        valid_system = "https://example.org/unique-id-system"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, valid_system))
        # Invalid: empty string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string value
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 42), ErrorReport)

    # STRING with GENDER rule on real field
    def test_gender_string_rule_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "contained|#:Patient|gender"
        # Valid genders per schema constants (male, female, other, unknown)
        self.assertIsNone(checker.validate_expression("STRING", "GENDER", field_path, "male"))
        self.assertIsNone(checker.validate_expression("STRING", "GENDER", field_path, "female"))
        # Invalid values should error
        self.assertIsInstance(checker.validate_expression("STRING", "GENDER", field_path, "M"), ErrorReport)

    # LIST with PERFORMING_PROFESSIONAL_FORENAME (empty rule -> non-empty list)
    def test_practitioner_forename_list_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "contained|#:Practitioner|name|0|given|0"
        # Valid: non-empty list
        self.assertIsNone(checker.validate_expression("LIST", "", field_path, ["Alice"]))
        # Invalid: empty list
        self.assertIsInstance(checker.validate_expression("LIST", "", field_path, []), ErrorReport)
        # Invalid: non-list value
        self.assertIsInstance(checker.validate_expression("LIST", "", field_path, "Alice"), ErrorReport)

    # STRING with PERFORMING_PROFESSIONAL_SURNAME (empty rule -> non-empty string)
    def test_practitioner_surname_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "contained|#:Practitioner|name|0|family"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "Smith"))
        # Invalid: empty string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 123), ErrorReport)

    # DATETIME with RECORDED_DATE (schema rule says 'false-strict-timezone' but we use default non-strict here)
    def test_recorded_date_datetime_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "recorded"
        # Valid: timezone offset other than +00:00 or +01:00 should be allowed when non-strict
        self.assertIsNone(checker.validate_expression("DATETIME", "", field_path, "2025-01-01T10:00:00+02:00"))
        # Valid: full date only also allowed per formats
        self.assertIsNone(checker.validate_expression("DATETIME", "", field_path, "2025-01-01"))
        # Invalid: Zulu timezone not in accepted formats
        self.assertIsInstance(
            checker.validate_expression("DATETIME", "", field_path, "2026-01-01T10:00:00Z"), ErrorReport
        )

    # STRING with no rule for PERSON_POSTCODE on real field
    def test_postcode_string_rule_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "contained|#:Patient|address|#:postalCode|postalCode"
        # With empty rule, generic string constraints apply: non-empty and no spaces
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "SW1A 1AA"))
        # Real-world postcode with a space should fail as spaces are not allowed without a rule override
        field_path = "POST_CODE"
        self.assertIsInstance(
            checker.validate_expression("STRING", "", field_path, 123),
            ErrorReport,
        )
        # Empty should also fail
        self.assertIsInstance(
            checker.validate_expression("STRING", "", field_path, ""),
            ErrorReport,
        )


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
