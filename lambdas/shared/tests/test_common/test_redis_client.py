import importlib
import unittest
from unittest.mock import Mock, patch

import common.redis_client as redis_client


class TestRedisClient(unittest.TestCase):
    REDIS_HOST = "mock-redis-host"
    REDIS_PORT = 6379
    REDIS_SSL = "true"
    REDIS_AUTH_TOKEN_SECRET_NAME = "mock-redis-auth-token-secret"

    def setUp(self):
        self.env = {
            "REDIS_HOST": self.REDIS_HOST,
            "REDIS_PORT": self.REDIS_PORT,
            "REDIS_SSL": self.REDIS_SSL,
        }

        self.getenv_patch = patch("os.getenv")
        self.mock_getenv = self.getenv_patch.start()
        self.mock_getenv.side_effect = lambda key, default=None: self.env.get(key, default)

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
        self.assertTrue(redis_client.REDIS_SSL)
        self.assertEqual(redis_client.REDIS_AUTH_TOKEN_SECRET_NAME, "")

    def test_redis_client(self):
        """Test redis client is not initialized on import"""
        importlib.reload(redis_client)
        self.mock_redis.assert_not_called()

    def test_redis_client_initialization(self):
        """Test redis client is initialized exactly once even with multiple invocations"""
        importlib.reload(redis_client)
        redis_client.get_redis_client()
        redis_client.get_redis_client()
        self.mock_redis.assert_called_once_with(
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            password=None,
            ssl=True,
            decode_responses=True,
        )
        self.assertTrue(hasattr(redis_client, "redis_client"))
        self.assertIsInstance(redis_client.redis_client, self.mock_redis.return_value.__class__)

    def test_redis_client_uses_auth_token_from_secrets_manager(self):
        """Test Redis auth token is fetched once from Secrets Manager"""
        self.env["REDIS_AUTH_TOKEN_SECRET_NAME"] = self.REDIS_AUTH_TOKEN_SECRET_NAME
        importlib.reload(redis_client)

        mock_secrets_manager_client = Mock()
        mock_secrets_manager_client.get_secret_value.return_value = {"SecretString": "mock-auth-token"}

        with patch("common.redis_client.get_secrets_manager_client", return_value=mock_secrets_manager_client):
            redis_client.get_redis_client()
            redis_client.get_redis_client()

        mock_secrets_manager_client.get_secret_value.assert_called_once_with(SecretId=self.REDIS_AUTH_TOKEN_SECRET_NAME)
        self.mock_redis.assert_called_once_with(
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            password="mock-auth-token",
            ssl=True,
            decode_responses=True,
        )
