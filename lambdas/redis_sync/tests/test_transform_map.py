import unittest
from unittest.mock import patch

from constants import RedisCacheKey
from transform_map import transform_map


class TestTransformMap(unittest.TestCase):
    def setUp(self):
        self.mock_logger_info = patch("transform_map.logger.info").start()
        self.mock_logger_warning = patch("transform_map.logger.warning").start()
        self.mock_supplier_permissions = patch(
            "transform_map.transform_supplier_permissions",
            return_value={"result": "supplier"},
        ).start()
        self.mock_vaccine_map = patch("transform_map.transform_vaccine_map", return_value={"result": "vaccine"}).start()
        self.mock_validation_rules = patch("transform_map.transform_validation_rules").start()

    def tearDown(self):
        patch.stopall()

    def test_permissions_config_file_key_calls_supplier_permissions(self):
        data = {"some": "data"}
        result = transform_map(data, RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY)
        self.mock_supplier_permissions.assert_called_once_with(data)
        self.assertEqual(result, {"result": "supplier"})
        self.mock_logger_info.assert_any_call(
            "Transforming data for file type: %s",
            RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY,
        )

    def test_disease_mapping_file_key_calls_vaccine_map(self):
        data = {"other": "data"}
        self.mock_validation_rules.return_value = {"validation_rules": data}
        result = transform_map(data, RedisCacheKey.DISEASE_MAPPING_FILE_KEY)
        self.mock_vaccine_map.assert_called_once_with(data)
        self.assertEqual(result, {"result": "vaccine"})
        self.mock_logger_info.assert_any_call(
            "Transforming data for file type: %s",
            RedisCacheKey.DISEASE_MAPPING_FILE_KEY,
        )

    def test_validation_rules_file_key_calls_validation_rules(self):
        data = {"validation": "schema"}
        self.mock_validation_rules.return_value = {"validation_rules": data}
        result = transform_map(data, RedisCacheKey.VALIDATION_RULES_FILE_KEY)
        self.mock_validation_rules.assert_called_once_with(data)
        self.assertEqual(result, {"validation_rules": data})
        self.mock_logger_info.assert_any_call(
            "Transforming data for file type: %s",
            RedisCacheKey.VALIDATION_RULES_FILE_KEY,
        )
