import unittest
from unittest.mock import patch, MagicMock
from redis_cacher import RedisCacher


class TestRedisCacher(unittest.TestCase):
    def setUp(self):
        patcher = patch("redis.StrictRedis")
        self.addCleanup(patcher.stop)
        self.mock_strict_redis = patcher.start()
        self.mock_instance = MagicMock()
        self.mock_strict_redis.return_value = self.mock_instance

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()
        self.logger_error_patcher.stop()

    def test_successful_connection(self):
        self.mock_instance.ping.return_value = True
        cacher = RedisCacher("localhost", 6379)
        self.assertTrue(hasattr(cacher, "redis_client"))
        self.mock_instance.ping.assert_called_once()

    def test_failed_connection(self):
        self.mock_instance.ping.return_value = False
        cacher = RedisCacher("localhost", 6379)
        self.assertTrue(hasattr(cacher, "redis_client"))
        self.mock_instance.ping.assert_called_once()

    def test_get_cache_returns_dict(self):
        self.mock_instance.ping.return_value = True
        self.mock_instance.get.return_value = '{"foo": "bar"}'
        cacher = RedisCacher("localhost", 6379)
        result = cacher.get_cache("some_key")
        self.assertEqual(result, {"foo": "bar"})
        self.mock_instance.get.assert_called_once_with("some_key")

    def test_get_cache_returns_empty_dict(self):
        self.mock_instance.ping.return_value = True
        self.mock_instance.get.return_value = None
        cacher = RedisCacher("localhost", 6379)
        result = cacher.get_cache("missing_key")
        self.assertEqual(result, {})
        self.mock_instance.get.assert_called_once_with("missing_key")


if __name__ == "__main__":
    unittest.main()