
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

    def test_supplier_permissions(self):
        with open("./tests/test_data/expected_supplier_permissions.json") as f:
            expected = json.load(f)
        result = transform_supplier_permissions(self.supplier_data)
        self.assertEqual(result["supplier_permissions"], expected)

    def test_ods_code_to_supplier(self):
        with open("./tests/test_data/expected_ods_code_to_supplier.json") as f:
            expected = json.load(f)
        result = transform_supplier_permissions(self.supplier_data)
        self.assertEqual(result["ods_code_to_supplier"], expected)

    def test_dev_ods_code_to_supplier_dev(self):
        self.ods_code_to_supplier_file_tester("dev")

    def test_dev_ods_code_to_supplier_preprod(self):
        self.ods_code_to_supplier_file_tester("preprod")

    def test_dev_ods_code_to_supplier_prod(self):
        self.ods_code_to_supplier_file_tester("prod")

    def ods_code_to_supplier_file_tester(self, env):
        with open("./tests/test_data/expected_ods_code_to_supplier.json") as expected_file:
            expected = json.load(expected_file)
            file_path = f"../config/{env}/permissions_config.json"

            with open(file_path) as f:
                supplier_data = json.load(f)
                result = transform_supplier_permissions(supplier_data)
                result_data = result["ods_code_to_supplier"]
                if result_data != expected:
                    # loop through all keys and values to find the mismatch
                    for key in result_data:
                        if key not in expected:
                            print(f"Key: {key} not found")
                        elif result_data[key] != expected[key]:
                            print(f"Key: {key}, Result: {result_data[key]}, Expected: {expected[key]}")
                    self.assertEqual(result_data, expected)

    def test_empty_input(self):
        result = transform_supplier_permissions([])
        self.assertEqual(result, {
            "supplier_permissions": {},
            "ods_code_to_supplier": {},
        })
