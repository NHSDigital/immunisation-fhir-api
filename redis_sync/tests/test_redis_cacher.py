import unittest
import json
from unittest.mock import patch
from redis_cacher import RedisCacher
from constants import RedisCacheKey


class TestRedisCacher(unittest.TestCase):

    def setUp(self):
        # mock s3_reader and transform_map
        self.s3_reader_patcher = patch("redis_cacher.S3Reader")
        self.mock_s3_reader = self.s3_reader_patcher.start()
        self.transform_map_patcher = patch("redis_cacher.transform_map")
        self.mock_transform_map = self.transform_map_patcher.start()
        self.redis_client_patcher = patch("redis_cacher.redis_client")
        self.mock_redis_client = self.redis_client_patcher.start()

    def tearDown(self):
        self.s3_reader_patcher.stop()
        self.transform_map_patcher.stop()
        self.redis_client_patcher.stop()

    def test_upload(self):
        mock_data = '{"a": "b"}'
        mock_transformed_data = '{"b": "c"}'
        self.mock_s3_reader.read = unittest.mock.Mock()
        self.mock_s3_reader.read.return_value = mock_data
        self.mock_transform_map.return_value = mock_transformed_data

        bucket_name = "bucket"
        file_key = "file-key"
        result = RedisCacher.upload(bucket_name, file_key)

        self.mock_s3_reader.read.assert_called_once_with(bucket_name, file_key)
        self.mock_transform_map.assert_called_once_with(mock_data, file_key)
        self.mock_redis_client.set.assert_called_once_with(file_key, mock_transformed_data)
        self.assertTrue(result)

    def test_get_cached_config_json(self):
        """Test getting cached config JSON from Redis."""
        cache_key = "some-key"
        cached_data = '{"some-data-key": "some-data-value"}'
        self.mock_redis_client.get.return_value = cached_data
        result = RedisCacher.get_cached_config_json(cache_key)
        self.assertEqual(result, json.loads(cached_data))
        self.mock_redis_client.get.assert_called_once_with(cache_key)

    def test_get_cached_permissions_config_json(self):
        cached_permissions = '{"permissions": "perm_config"}'
        self.mock_redis_client.get.return_value = cached_permissions
        result = RedisCacher.get_cached_permissions_config_json()
        self.assertEqual(result, json.loads(cached_permissions))
        self.mock_redis_client.get.assert_called_once_with(RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY)

    def test_get_cached_disease_mapping_json(self):
        cached_disease_mapping = '{"disease": "disease-mapping"}'
        self.mock_redis_client.get.return_value = cached_disease_mapping
        result = RedisCacher.get_cached_disease_mapping_json()
        self.assertEqual(result, json.loads(cached_disease_mapping))
        self.mock_redis_client.get.assert_called_once_with(RedisCacheKey.DISEASE_MAPPING_FILE_KEY)