import unittest
import json
from unittest.mock import patch
from transform_vaccine_map import transform_vaccine_map


# Import the sample input from the sample_data module
with open("./tests/test_data/disease_mapping.json") as f:
    sample_map = json.load(f)


class TestTransformVaccineMap(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()

    def test_transform_vaccine_map(self):
        result = transform_vaccine_map(sample_map)
        # Check that all vaccine keys are present and map to the correct diseases
        for entry in sample_map:
            self.assertIn(entry["vacc_type"], result["vaccine"])
            self.assertEqual(result["vaccine"][entry["vacc_type"]], entry["diseases"])
        # Check that all disease keys are present and map to the correct vaccine
        for entry in sample_map:
            disease_codes = ':'.join(sorted(d["code"] for d in entry["diseases"]))
            self.assertIn(disease_codes, result["disease"])
            self.assertEqual(result["disease"][disease_codes], entry["vacc_type"])

    def test_disease_to_vacc(self):
        """ Test that the disease to vaccine mapping is correct."""
        with open("./tests/test_data/expected_disease_to_vacc.json") as f:
            expected_disease_to_vacc = json.load(f)
            result = transform_vaccine_map(sample_map)
            self.assertEqual(result["disease"], expected_disease_to_vacc)

    def test_vacc_to_diseases(self):

        with open("./tests/test_data/expected_vacc_to_diseases.json") as f:
            expected_vacc_to_diseases = json.load(f)

            result = transform_vaccine_map(sample_map)
            self.assertEqual(result["vaccine"], expected_vacc_to_diseases)
