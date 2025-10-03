
import unittest
import json
from unittest.mock import patch
from transform_configs import transform_vaccine_map, transform_supplier_permissions, transform_generic


class TestBase(unittest.TestCase):
    def setUp(self):
        self.mock_logger_info = patch("transform_configs.logger.info").start()
        self.mock_logger_warning = patch("transform_configs.logger.warning").start()

    def tearDown(self):
        patch.stopall()


class TestTransformConfigs(TestBase):
    def setUp(self):
        super().setUp()

        with open("./tests/test_data/disease_mapping.json") as mapping_data:
            self.sample_map = json.load(mapping_data)

        with open("./tests/test_data/permissions_config.json") as permissions_data:
            self.supplier_data = json.load(permissions_data)

    def tearDown(self):
        super().tearDown()

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

    def test_empty_input(self):
        result = transform_supplier_permissions([])
        self.assertEqual(result, {
            "supplier_permissions": {},
            "ods_code_to_supplier": {},
        })


class TestTransformGeneric(TestBase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_json_file_transformation(self):
        data = {"name": "test"}
        file_type = "example.json"
        expected = {"example_json": data}
        result = transform_generic(data, file_type)
        self.assertEqual(result, expected)

    def test_json_file_with_uppercase_extension(self):
        data = {"key": "value"}
        file_type = "SamPle.JSON"
        expected = {"sample_json": data}
        result = transform_generic(data, file_type)
        self.assertEqual(result, expected)

    def test_unrecognized_file_type_returns_empty_dict(self):
        data = {"key1": "value1"}
        file_type = "example.txt"
        result = transform_generic(data, file_type)
        self.assertEqual(result, {})

    @patch('logging.getLogger')
    def test_warning_logged_for_unrecognized_file_type(self, mock_get_logger):
        file_type = "unsupported.csv"
        transform_generic({}, file_type)
        self.mock_logger_warning.assert_called_once_with(
            f"Unrecognized file type: {file_type}."
        )
