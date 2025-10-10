import json
import unittest
from unittest.mock import patch

from transform_configs import (
    transform_supplier_permissions,
    transform_vaccine_map,
    transform_validation_rules,
)


class TestTransformConfigs(unittest.TestCase):
    def setUp(self):
        self.mock_logger_info = patch("transform_configs.logger.info").start()
        self.mock_logger_warning = patch("transform_configs.logger.warning").start()

        with open("./tests/test_data/disease_mapping.json") as mapping_data:
            self.sample_map = json.load(mapping_data)

        with open("./tests/test_data/permissions_config.json") as permissions_data:
            self.supplier_data = json.load(permissions_data)

    def tearDown(self):
        patch.stopall()

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

    def test_validation_rules(self):
        # validation schema is simple json returned as is to key "validation_rules"
        sample_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = transform_validation_rules(sample_schema)
        self.assertEqual(result, {"validation_rules": sample_schema})

    def test_empty_input(self):
        result = transform_supplier_permissions([])
        self.assertEqual(
            result,
            {
                "supplier_permissions": {},
                "ods_code_to_supplier": {},
            },
        )
