# flake8: noqa: F811

import unittest
import json
from unittest.mock import patch
from transform_configs import transform_vaccine_map, transform_supplier_permissions


# Import the sample input from the sample_data module
with open("./tests/test_data/disease_mapping.json") as f:
    sample_map = json.load(f)

with open("./tests/test_data/permissions_config.json") as permissions_data:
    supplier_data = json.load(permissions_data)


    class TestTransformConfigs(unittest.TestCase):

        def setUp(self):
            self.logger_info_patcher = patch("logging.Logger.info")
            self.mock_logger_info = self.logger_info_patcher.start()

        def tearDown(self):
            self.logger_info_patcher.stop()

        def test_disease_to_vacc(self):
            """ Test that the disease to vaccine mapping is correct."""
            with open("./tests/test_data/expected_disease_to_vacc.json") as f:
                expected_disease_to_vacc = json.load(f)
                result = transform_vaccine_map(sample_map)
                self.assertEqual(result["diseases_to_vacc"], expected_disease_to_vacc)

        def test_vacc_to_diseases(self):
            with open("./tests/test_data/expected_vacc_to_diseases.json") as f:
                expected_vacc_to_diseases = json.load(f)
                result = transform_vaccine_map(sample_map)
                self.assertEqual(result["vacc_to_diseases"], expected_vacc_to_diseases)
        
        def test_permissions_expected_output_file(self):
            with open("./tests/test_data/expected_perms.json") as permissions_data:
                expected_supplier_data = json.load(permissions_data) 
            result = transform_supplier_permissions(supplier_data)
            self.assertEqual(result, expected_supplier_data)

        def test_empty_input(self):
            result = transform_supplier_permissions([])
            self.assertEqual(result, {"supplier_permissions": {}})

        def test_missing_keys_raises_error(self):
            broken_input = [{"supplier": "X"}, {"permissions": ["read:vaccine"]}]
            with self.assertRaises(KeyError):
                transform_supplier_permissions(broken_input)
