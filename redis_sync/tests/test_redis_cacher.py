import unittest
from unittest.mock import patch
from redis_cacher import RedisCacher


class TestRedisCacher(unittest.TestCase):

    def setUp(self):
        # mock s3_reader and transform_map
        self.s3_reader_patcher = patch("redis_cacher.S3Reader")
        self.mock_s3_reader = self.s3_reader_patcher.start()
        self.transform_map_patcher = patch("redis_cacher.transform_map")
        self.mock_transform_map = self.transform_map_patcher.start()
        self.redis_client_patcher = patch("redis_cacher.redis_client")
        self.mock_redis_client = self.redis_client_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.s3_reader_patcher.stop()
        self.transform_map_patcher.stop()
        self.redis_client_patcher.stop()
        self.logger_info_patcher.stop()

    def test_upload(self):
        mock_data = {"a": "b"}
        mock_transformed_data = {
            "vacc_to_diseases": {"b": "c"},
            "diseases_to_vacc": {"c": "b"}
        }

        self.mock_s3_reader.read = unittest.mock.Mock()
        self.mock_s3_reader.read.return_value = mock_data
        self.mock_transform_map.return_value = mock_transformed_data

        bucket_name = "bucket"
        file_key = "file-key"
        result = RedisCacher.upload(bucket_name, file_key)

        self.mock_s3_reader.read.assert_called_once_with(bucket_name, file_key)
        self.mock_transform_map.assert_called_once_with(mock_data, file_key)
        self.mock_redis_client.hmset.assert_called()
        self.assertEqual(result, {"status": "success", "message": f"File {file_key} uploaded to Redis cache."})
