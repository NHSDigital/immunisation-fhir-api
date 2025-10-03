
import unittest
from unittest.mock import patch
from transform_map import transform_map
from constants import RedisCacheKey


class TestTransformMap(unittest.TestCase):
    def setUp(self):
        self.mock_logger_info = patch("transform_map.logger.info").start()
        self.mock_logger_warning = patch("transform_map.logger.warning").start()
        self.mock_supplier_permissions = patch("transform_map.transform_supplier_permissions",
                                               return_value={"result": "supplier"}).start()
        self.mock_vaccine_map = patch("transform_map.transform_vaccine_map", return_value={"result": "vaccine"}).start()
        self.mock_generic = patch("transform_map.transform_generic", return_value={"result": "generic"}).start()

    def tearDown(self):
        patch.stopall()

    def test_permissions_config_file_key_calls_supplier_permissions(self):
        data = {"some": "data"}
        result = transform_map(data, RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY)
        self.mock_supplier_permissions.assert_called_once_with(data)
        self.assertEqual(result, {"result": "supplier"})
        self.mock_logger_info.assert_any_call(
            "Transforming data for file type: %s", RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY)

    def test_disease_mapping_file_key_calls_vaccine_map(self):
        data = {"other": "data"}
        result = transform_map(data, RedisCacheKey.DISEASE_MAPPING_FILE_KEY)
        self.mock_vaccine_map.assert_called_once_with(data)
        self.assertEqual(result, {"result": "vaccine"})
        self.mock_logger_info.assert_any_call(
            "Transforming data for file type: %s", RedisCacheKey.DISEASE_MAPPING_FILE_KEY)

    def test_other_file_type_calls_generic(self):
        data = {"generic": "data"}
        file_type = "unknown_file_type"
        result = transform_map(data, file_type)
        self.mock_generic.assert_called_once_with(data, file_type)
        self.assertEqual(result, {"result": "generic"})
        self.mock_logger_info.assert_any_call("No specific transformation defined for file type: %s", file_type)
