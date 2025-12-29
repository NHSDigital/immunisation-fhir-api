import unittest
from copy import deepcopy

from common.data_quality.completeness import DataQualityCompletenessChecker, MissingFields
from test_common.data_quality.sample_values import VALID_BATCH_IMMUNISATION


class TestDataQualityCompletenessChecker(unittest.TestCase):
    def setUp(self):
        self.DataQualityCompletenessChecker = DataQualityCompletenessChecker()

    def test_check_completeness_no_missing_fields(self):
        complete_immunisation = deepcopy(VALID_BATCH_IMMUNISATION)

        expected_missing_fields = MissingFields(required_fields=[], mandatory_fields=[], optional_fields=[])

        actual_missing_fields = self.DataQualityCompletenessChecker.run_checks(complete_immunisation)

        self.assertEqual(expected_missing_fields, actual_missing_fields)

    def test_check_completeness_empty_strings(self):
        incomplete_immunisation = deepcopy(VALID_BATCH_IMMUNISATION)
        incomplete_immunisation["NHS_NUMBER"] = ""  # required
        incomplete_immunisation["PERSON_FORENAME"] = ""  # mandatory
        incomplete_immunisation["PERFORMING_PROFESSIONAL_FORENAME"] = ""  # optional

        expected_missing_fields = MissingFields(
            required_fields=["NHS_NUMBER"],
            mandatory_fields=["PERSON_FORENAME"],
            optional_fields=["PERFORMING_PROFESSIONAL_FORENAME"],
        )

        actual_missing_fields = self.DataQualityCompletenessChecker.run_checks(incomplete_immunisation)

        self.assertEqual(expected_missing_fields, actual_missing_fields)

    def test_check_completeness_missing(self):
        incomplete_immunisation = deepcopy(VALID_BATCH_IMMUNISATION)
        incomplete_immunisation.pop("NHS_NUMBER")  # required
        incomplete_immunisation.pop("PERSON_FORENAME")  # mandatory
        incomplete_immunisation.pop("PERFORMING_PROFESSIONAL_FORENAME")  # optional

        expected_missing_fields = MissingFields(
            required_fields=["NHS_NUMBER"],
            mandatory_fields=["PERSON_FORENAME"],
            optional_fields=["PERFORMING_PROFESSIONAL_FORENAME"],
        )

        actual_missing_fields = self.DataQualityCompletenessChecker.run_checks(incomplete_immunisation)

        self.assertEqual(expected_missing_fields, actual_missing_fields)

    def test_check_completeness_multiple_missing(self):
        incomplete_immunisation = deepcopy(VALID_BATCH_IMMUNISATION)
        incomplete_immunisation.pop("NHS_NUMBER")  # required
        incomplete_immunisation.pop("VACCINATION_PROCEDURE_TERM")  # required
        incomplete_immunisation.pop("PERSON_FORENAME")  # mandatory
        incomplete_immunisation.pop("PERSON_SURNAME")  # mandatory
        incomplete_immunisation.pop("PERFORMING_PROFESSIONAL_FORENAME")  # optional
        incomplete_immunisation.pop("PERFORMING_PROFESSIONAL_SURNAME")  # optional

        expected_missing_fields = MissingFields(
            required_fields=["NHS_NUMBER", "VACCINATION_PROCEDURE_TERM"],
            mandatory_fields=["PERSON_FORENAME", "PERSON_SURNAME"],
            optional_fields=["PERFORMING_PROFESSIONAL_FORENAME", "PERFORMING_PROFESSIONAL_SURNAME"],
        )

        actual_missing_fields = self.DataQualityCompletenessChecker.run_checks(incomplete_immunisation)

        self.assertEqual(expected_missing_fields, actual_missing_fields)
