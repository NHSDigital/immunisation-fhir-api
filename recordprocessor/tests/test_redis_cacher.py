import unittest
from unittest.mock import patch, MagicMock
from redis_cacher import RedisCacher


class TestRedisCacher(unittest.TestCase):
    def setUp(self):

        self.strict_redis_patcher = patch("redis.StrictRedis")
        self.strict_redis = self.strict_redis_patcher.start()
        self.mock_redis_client = MagicMock()
        self.strict_redis.return_value = self.mock_redis_client

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        self.strict_redis_patcher.stop()
        self.logger_info_patcher.stop()
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_error_patcher.stop()

    def test_successful_connection(self):
        self.mock_redis_client.ping.return_value = True
        cacher = RedisCacher("localhost", 6379)
        self.assertTrue(hasattr(cacher, "redis_client"))
        self.mock_logger_info.assert_called_once()
        self.mock_redis_client.ping.assert_called_once()
        print("test_successful_connection...Done")

    def test_failed_connection(self):
        self.mock_redis_client.ping.return_value = False
        cacher = RedisCacher("localhost", 6379)
        self.assertTrue(hasattr(cacher, "redis_client"))
        self.mock_redis_client.ping.assert_called_once()
        print("test_failed_connection...Done")

    def test_get_cache_returns_dict(self):
        self.mock_redis_client.ping.return_value = True
        self.mock_redis_client.get.return_value = '{"foo": "bar"}'
        cacher = RedisCacher("localhost", 6379)
        result = cacher.get_cache("some_key")
        self.assertEqual(result, {"foo": "bar"})
        self.mock_redis_client.get.assert_called_once_with("some_key")
        print("test_get_cache_returns_dict...Done")

    def test_get_cache_returns_empty_dict(self):
        self.mock_redis_client.ping.return_value = True
        self.mock_redis_client.get.return_value = None
        cacher = RedisCacher("localhost", 6379)
        result = cacher.get_cache("missing_key")
        self.assertEqual(result, {})
        self.mock_redis_client.get.assert_called_once_with("missing_key")


if __name__ == "__main__":
    unittest.main()
