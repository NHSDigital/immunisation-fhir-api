import unittest
from unittest.mock import patch
from redis_cacher import RedisCacher


class TestRedisCacher(unittest.TestCase):

    def setUp(self):
        self.mock_s3_reader = patch("redis_cacher.S3Reader").start()
        self.mock_transform_map = patch("redis_cacher.transform_map").start()
        self.mock_redis_client = patch("common.redis_client.redis_client").start()
        self.mock_logger_info = patch("logging.Logger.info").start()
        self.mock_logger_warning = patch("logging.Logger.warning").start()

    def tearDown(self):
        patch.stopall()

    def test_upload(self):
        mock_data = {"a": "b"}
        mock_transformed_data = {
            "vacc_to_diseases": {"b": "c"},
            "diseases_to_vacc": {"c": "b"},
        }

        self.mock_s3_reader.read = unittest.mock.Mock()
        self.mock_s3_reader.read.return_value = mock_data
        self.mock_transform_map.return_value = mock_transformed_data

        bucket_name = "bucket"
        file_key = "file-key"
        result = RedisCacher.upload(bucket_name, file_key)

        self.mock_s3_reader.read.assert_called_once_with(bucket_name, file_key)
        self.mock_transform_map.assert_called_once_with(mock_data, file_key)
        self.mock_redis_client.hmset.assert_any_call("vacc_to_diseases", {"b": "c"})
        self.mock_redis_client.hmset.assert_any_call("diseases_to_vacc", {"c": "b"})
        self.mock_redis_client.hdel.assert_not_called()
        self.assertEqual(
            result,
            {
                "status": "success",
                "message": f"File {file_key} uploaded to Redis cache.",
            },
        )

    def test_deletes_extra_fields(self):
        mock_data = {"input_key": "input_val"}
        mock_transformed_data = {
            "hash_name": {
                "transformed_key_1": "transformed_val_1",
                "transformed_key_2": "transformed_val_2",
            },
        }

        self.mock_s3_reader.read = unittest.mock.Mock()
        self.mock_s3_reader.read.return_value = mock_data
        self.mock_transform_map.return_value = mock_transformed_data
        self.mock_redis_client.hgetall.return_value = {
            "obsolete_key_1": "obsolete_val_1",
            "obsolete_key_2": "obsolete_val_2",
            "transformed_key_2": "transformed_val_2",
        }

        bucket_name = "bucket"
        file_key = "file-key"
        result = RedisCacher.upload(bucket_name, file_key)

        self.mock_s3_reader.read.assert_called_once_with(bucket_name, file_key)
        self.mock_transform_map.assert_called_once_with(mock_data, file_key)
        self.mock_redis_client.hgetall.assert_called_once_with("hash_name")
        self.mock_redis_client.hmset.assert_called_once_with(
            "hash_name",
            {
                "transformed_key_1": "transformed_val_1",
                "transformed_key_2": "transformed_val_2",
            },
        )
        self.mock_redis_client.hdel.assert_called_once_with("hash_name", "obsolete_key_1", "obsolete_key_2")
        self.assertEqual(
            result,
            {
                "status": "success",
                "message": f"File {file_key} uploaded to Redis cache.",
            },
        )

    def test_unrecognised_format(self):
        mock_data = {"a": "b"}

        self.mock_s3_reader.read = unittest.mock.Mock()
        self.mock_s3_reader.read.return_value = mock_data
        self.mock_transform_map.return_value = {}

        bucket_name = "bucket"
        file_key = "file-key.my_yaml"
        result = RedisCacher.upload(bucket_name, file_key)

        self.mock_s3_reader.read.assert_called_once_with(bucket_name, file_key)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(
            result["message"],
            f"No valid Redis mappings found for file '{file_key}'. Nothing uploaded.",
        )
        self.mock_logger_warning.assert_called_once()
        self.mock_redis_client.hmset.assert_not_called()
        self.mock_redis_client.hdel.assert_not_called()
