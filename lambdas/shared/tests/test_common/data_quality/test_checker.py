import copy
import datetime
import unittest
from unittest.mock import patch

from common.data_quality.checker import DataQualityChecker
from common.data_quality.completeness import DataQualityCompletenessChecker
from test_common.data_quality.sample_values import VALID_BATCH_IMMUNISATION


class TestDataQualityChecker(unittest.TestCase):
    def setUp(self):
        # Fix date.today() for all validation tests
        date_today_patcher = patch("common.data_quality.models.immunization_batch_row_model.datetime", wraps=datetime)
        self.mock_date_today = date_today_patcher.start()
        self.mock_date_today.date.today.return_value = datetime.date(2024, 5, 20)

        completeness_checker = DataQualityCompletenessChecker()
        self.batch_dq_checker = DataQualityChecker(completeness_checker, is_batch_csv=True)
        self.fhir_json_dq_checker = DataQualityChecker(completeness_checker, is_batch_csv=False)

    def test_check_validity_returns_empty_list_when_data_is_valid(self):
        validation_result = self.batch_dq_checker._check_validity(VALID_BATCH_IMMUNISATION)

        self.assertEqual([], validation_result)

    def test_check_validity_returns_list_of_invalid_fields_when_invalid_data_provided(self):
        test_cases = [
            ("NHS_NUMBER", "1234"),  # Failing min length
            ("NHS_NUMBER", "1234543543543543534"),  # Failing max length
            ("NHS_NUMBER", "900000AB09"),  # Failing digit only check
            ("PERSON_DOB", "18990101"),  # Prior to min accepted past date
            ("PERSON_DOB", "20240137"),  # Invalid date
            ("PERSON_DOB", "20240624"),  # Past dates only
            ("DATE_AND_TIME", "17000511T120000"),  # Prior to min accepted past date
            ("DATE_AND_TIME", "20241511T120000"),  # Invalid datetime
            ("DATE_AND_TIME", "20241511T120"),  # Invalid datetime
            ("DATE_AND_TIME", "20240520T120001"),  # Past dates only
            ("PERSON_POSTCODE", "AAA12 3B"),
            ("EXPIRY_DATE", "18990101"),  # Prior to min accepted past date
            ("EXPIRY_DATE", "20240137"),  # Invalid date
            ("EXPIRY_DATE", "20250521"),  # Expiry greater than a year away
            ("DOSE_AMOUNT", "abd"),  # Not a decimal value
            ("DOSE_AMOUNT", "5.67"),  # Decimal value but not in the permitted list of values
            ("SITE_OF_VACCINATION_CODE", "1254"),  # Fails snomed code min length
            ("SITE_OF_VACCINATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("SITE_OF_VACCINATION_CODE", "18756hg098"),  # Fails regex
            ("ROUTE_OF_VACCINATION_CODE", "1254"),  # Fails snomed code min length
            ("ROUTE_OF_VACCINATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("ROUTE_OF_VACCINATION_CODE", "18756hg098"),  # Fails regex
            ("DOSE_UNIT_CODE", "415818088"),  # Dose unit code not in the enums
            ("INDICATION_CODE", "1254"),  # Fails snomed code min length
            ("INDICATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("INDICATION_CODE", "18756hg098"),  # Fails regex
        ]

        for field, failing_value in test_cases:
            with self.subTest(field=field, failing_value=failing_value):
                invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
                invalid_batch_imms_payload[field] = failing_value

                validation_result = self.batch_dq_checker._check_validity(invalid_batch_imms_payload)

                self.assertEqual([field], validation_result)

    def test_check_validity_returns_list_of_multiple_invalid_fields_for_multiple_failures(self):
        invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
        invalid_batch_imms_payload["NHS_NUMBER"] = "12345678901"
        invalid_batch_imms_payload["EXPIRY_DATE"] = "20240137"
        invalid_batch_imms_payload["PERSON_POSTCODE"] = "12 ACX"
        invalid_batch_imms_payload["DOSE_AMOUNT"] = "6.789"
        invalid_batch_imms_payload["INDICATION_CODE"] = "123"

        validation_result = self.batch_dq_checker._check_validity(invalid_batch_imms_payload)

        self.assertEqual(
            ["NHS_NUMBER", "PERSON_POSTCODE", "EXPIRY_DATE", "DOSE_AMOUNT", "INDICATION_CODE"], validation_result
        )
