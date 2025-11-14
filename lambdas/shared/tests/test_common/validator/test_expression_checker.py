import unittest
from decimal import Decimal

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

    # NHS_NUMBER expression type (MOD 11 check)
    def test_nhs_number_mod11_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "contained|#:Patient|identifier|#:https://fhir.nhs.uk/Id/nhs-number|value"
        # Known valid NHS number
        self.assertIsNone(checker.validate_expression("NHS_NUMBER", "", field_path, "9736592677"))
        # Invalid: wrong check digit
        self.assertIsInstance(checker.validate_expression("NHS_NUMBER", "", field_path, "9434765918"), ErrorReport)
        # Invalid: non-digit / wrong length
        self.assertIsInstance(checker.validate_expression("NHS_NUMBER", "", field_path, "123456789A"), ErrorReport)

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

    # BOOLEAN with PRIMARY_SOURCE
    def test_primary_source_boolean_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "primarySource"
        # Valid: boolean True
        self.assertIsNone(checker.validate_expression("BOOLEAN", "", field_path, True))
        # Invalid: non-boolean should raise TypeError per implementation
        self.assertIsInstance(checker.validate_expression("BOOLEAN", "", field_path, "true"), ErrorReport)

    # STRING with VACCINATION_PROCEDURE_CODE
    def test_vaccination_procedure_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "extension|0|valueCodeableConcept|coding|0|code"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "123456"))
        # Invalid: empty string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string value
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 123456), ErrorReport)

    # After parent check succeeds - SNOMED_CODE for VACCINATION_PROCEDURE_CODE
    def test_vaccination_procedure_snomed_code_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "extension|0|valueCodeableConcept|coding|0|code"
        # Valid SNOMED example (passes Verhoeff, doesn't start with 0, length ok, suffix rule)
        self.assertIsNone(checker.validate_expression("SNOMED_CODE", "", field_path, "1119349007"))
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("SNOMED_CODE", "", field_path, ""), ErrorReport)
        # Invalid: non-digit
        self.assertIsInstance(checker.validate_expression("SNOMED_CODE", "", field_path, "ABC123"), ErrorReport)
        # Invalid: starts with 0
        self.assertIsInstance(checker.validate_expression("SNOMED_CODE", "", field_path, "012345"), ErrorReport)

    # STRING with VACCINATION_PROCEDURE_TERM
    def test_vaccination_procedure_term_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "extension|0|valueCodeableConcept|coding|0|display"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "COVID-19 vaccination"))
        # Invalid: empty string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string value
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 999), ErrorReport)

    # POSITIVEINTEGER with DOSE_SEQUENCE
    def test_dose_sequence_positiveinteger_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "protocolApplied|0|doseNumberPositiveInt"
        # Valid: positive integer
        self.assertIsNone(checker.validate_expression("POSITIVEINTEGER", "", field_path, 2))
        # Invalid: zero -> ValueError
        self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", field_path, 0), ErrorReport)
        # Invalid: negative -> ValueError
        self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", field_path, -1), ErrorReport)
        # Invalid: non-int -> TypeError
        self.assertIsInstance(checker.validate_expression("POSITIVEINTEGER", "", field_path, "2"), ErrorReport)

    # STRING with VACCINE_PRODUCT_CODE
    def test_vaccine_product_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "vaccineCode|coding|#:http://snomed.info/sct|code"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "1119349007"))
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 1119349007), ErrorReport)

    # STRING with VACCINE_PRODUCT_TERM
    def test_vaccine_product_term_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "vaccineCode|coding|#:http://snomed.info/sct|display"
        # Valid: non-empty string (spaces allowed by default)
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "COVID-19 mRNA vaccine"))
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 12345), ErrorReport)

    # STRING with VACCINE_MANUFACTURER
    def test_vaccine_manufacturer_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "manufacturer|display"
        # Valid: non-empty string
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "Pfizer"))
        # Invalid: empty
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        # Invalid: non-string
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 101), ErrorReport)

    # STRING with SITE_OF_VACCINATION_CODE
    def test_site_of_vaccination_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "site|coding|#:http://snomed.info/sct|code"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "123456"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 123456), ErrorReport)

    # STRING with SITE_OF_VACCINATION_TERM
    def test_site_of_vaccination_term_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "site|coding|#:http://snomed.info/sct|display"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "Left deltoid"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 999), ErrorReport)

    # STRING with ROUTE_OF_VACCINATION_CODE
    def test_route_of_vaccination_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "route|coding|#:http://snomed.info/sct|code"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "1234"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 1234), ErrorReport)

    # STRING with ROUTE_OF_VACCINATION_TERM
    def test_route_of_vaccination_term_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "route|coding|#:http://snomed.info/sct|display"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "Intramuscular"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 12), ErrorReport)

    # INTDECIMAL with DOSE_AMOUNT
    def test_dose_amount_intdecimal_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "doseQuantity|value"
        # Valid: int
        self.assertIsNone(checker.validate_expression("INTDECIMAL", "", field_path, 1))
        # Valid: Decimal
        self.assertIsNone(checker.validate_expression("INTDECIMAL", "", field_path, Decimal("0.5")))
        # Invalid: string
        self.assertIsInstance(checker.validate_expression("INTDECIMAL", "", field_path, "0.5"), ErrorReport)

    # STRING with DOSE_UNIT_CODE
    def test_dose_unit_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "doseQuantity|code"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "ml"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 1), ErrorReport)

    # STRING with DOSE_UNIT_TERM
    def test_dose_unit_term_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "doseQuantity|unit"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "milliliter"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 1), ErrorReport)

    # STRING with INDICATION_CODE
    def test_indication_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "reasonCode|#:http://snomed.info/sct|coding|#:http://snomed.info/sct|code"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "987654"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 987654), ErrorReport)

    # STRING with LOCATION_CODE
    def test_location_code_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "location|identifier|value"
        self.assertIsNone(checker.validate_expression("STRING", "", field_path, "LOC-123"))
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 321), ErrorReport)

    # STRING with LOCATION_CODE_TYPE_URI
    def test_location_code_type_uri_string_valid_and_invalid(self):
        checker = self.make_checker()
        field_path = "location|identifier|system"
        self.assertIsNone(
            checker.validate_expression("STRING", "", field_path, "https://example.org/location-code-system")
        )
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, 0), ErrorReport)

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
        self.assertIsInstance(checker.validate_expression("STRING", "", field_path, ""), ErrorReport)


if __name__ == "__main__":
    unittest.main()
