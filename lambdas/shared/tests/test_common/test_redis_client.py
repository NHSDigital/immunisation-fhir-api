import importlib
import unittest
from unittest.mock import patch

import common.redis_client as redis_client


class TestRedisClient(unittest.TestCase):
    REDIS_HOST = "mock-redis-host"
    REDIS_PORT = 6379

    def setUp(self):
        self.getenv_patch = patch("os.getenv")
        self.mock_getenv = self.getenv_patch.start()
        self.mock_getenv.side_effect = lambda key, default=None: {
            "REDIS_HOST": self.REDIS_HOST,
            "REDIS_PORT": self.REDIS_PORT,
        }.get(key, default)

        self.redis_patch = patch("redis.StrictRedis")
        self.mock_redis = self.redis_patch.start()

        self.mock_redis.return_value = self.mock_redis

    def tearDown(self):
        patch.stopall()

    def test_os_environ(self):
        # Test if environment variables are set correctly
        importlib.reload(redis_client)
        self.assertEqual(redis_client.REDIS_HOST, self.REDIS_HOST)
        self.assertEqual(redis_client.REDIS_PORT, self.REDIS_PORT)

    def test_redis_client(self):
        """Test redis client is not initialized on import"""
        importlib.reload(redis_client)
        self.mock_redis.assert_not_called()

    def test_redis_client_initialization(self):
        """Test redis client is initialized exactly once even with multiple invocations"""
        importlib.reload(redis_client)
        redis_client.get_redis_client()
        redis_client.get_redis_client()
        self.mock_redis.assert_called_once_with(host=self.REDIS_HOST, port=self.REDIS_PORT, decode_responses=True)
        self.assertTrue(hasattr(redis_client, "redis_client"))
        self.assertIsInstance(redis_client.redis_client, self.mock_redis.return_value.__class__)
