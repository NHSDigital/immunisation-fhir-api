
import unittest
import json
from unittest.mock import patch
from transform_configs import transform_vaccine_map, transform_supplier_permissions


class TestTransformConfigs(unittest.TestCase):
    def setUp(self):
        self.logger_info_patcher = patch("transform_configs.logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        with open("./tests/test_data/disease_mapping.json") as mapping_data:
            self.sample_map = json.load(mapping_data)

        with open("./tests/test_data/permissions_config.json") as permissions_data:
            self.supplier_data = json.load(permissions_data)

    def tearDown(self):
        self.logger_info_patcher.stop()

    def test_disease_to_vacc(self):
        with open("./tests/test_data/expected_disease_to_vacc.json") as f:
            expected = json.load(f)
        result = transform_vaccine_map(self.sample_map)
        self.assertEqual(result["diseases_to_vacc"], expected)

    def test_vacc_to_diseases(self):
        with open("./tests/test_data/expected_vacc_to_diseases.json") as f:
            expected = json.load(f)
        result = transform_vaccine_map(self.sample_map)
        self.assertEqual(result["vacc_to_diseases"], expected)

    def test_transform_supplier_permissions_against_expected_file(self):
        with open("./tests/test_data/expected_perms.json") as f:
            expected = json.load(f)
        result = transform_supplier_permissions(self.supplier_data)
        self.assertEqual(result, expected)

    def test_empty_input(self):
        result = transform_supplier_permissions([])
        self.assertEqual(result, {"supplier_permissions": {}})

    def test_missing_keys_raises_error(self):
        broken_input = [{"supplier": "X"}, {"permissions": ["read:vaccine"]}]
        with self.assertRaises(KeyError):
            transform_supplier_permissions(broken_input)
