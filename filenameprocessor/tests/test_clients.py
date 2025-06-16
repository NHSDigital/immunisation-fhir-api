import unittest
from unittest.mock import patch
import clients as clients
import importlib


class TestClients(unittest.TestCase):

    BUCKET_NAME = "default-bucket"
    AWS_REGION = "eu-west-2"
    REDIS_HOST = "mock-redis-host"
    REDIS_PORT = 6379

    def setUp(self):
        # patch boto3_client
        self.boto3_client_patch = patch("boto3.client")
        self.mock_boto3_client = self.boto3_client_patch.start()
        # patch logging
        self.logging_patch = patch("logging.getLogger")
        self.mock_logging = self.logging_patch.start()

        self.getenv_patch = patch("os.getenv")
        self.mock_getenv = self.getenv_patch.start()
        self.mock_getenv.side_effect = lambda key, default=None: {
            "CONFIG_BUCKET_NAME": self.BUCKET_NAME,
            "AWS_REGION": self.AWS_REGION,
            "REDIS_HOST": self.REDIS_HOST,
            "REDIS_PORT": self.REDIS_PORT
        }.get(key, default)

        # patch redis
        self.redis_patch = patch("redis.StrictRedis")
        self.mock_redis = self.redis_patch.start()
        # default mock returns for redis and s3 client
        self.mock_redis.return_value = self.mock_redis
        self.mock_boto3_client.return_value = self.mock_boto3_client
        self.mock_boto3_client.return_value.send_message = {}

    def tearDown(self):
        self.getenv_patch.stop()
        self.boto3_client_patch.stop()
        self.logging_patch.stop()
        self.redis_patch.stop()

    def test_os_environ(self):
        # Test if environment variables are set correctly
        importlib.reload(clients)
        self.assertEqual(clients.CONFIG_BUCKET_NAME, self.BUCKET_NAME)
        self.assertEqual(clients.REGION_NAME, self.AWS_REGION)
        self.assertEqual(clients.REDIS_HOST, self.REDIS_HOST)
        self.assertEqual(clients.REDIS_PORT, self.REDIS_PORT)

    def test_boto3_client(self):
        ''' Test boto3 client is created with correct parameters '''
        importlib.reload(clients)
        self.mock_boto3_client.assert_called_once_with("s3", region_name=self.AWS_REGION)

    def test_redis_client(self):
        ''' Test redis client is created with correct parameters '''
        importlib.reload(clients)
        self.mock_redis.assert_called_once_with(
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            decode_responses=True
        )

    def test_logging_setup(self):
        ''' Test logging is set up correctly '''
        importlib.reload(clients)
        self.assertTrue(hasattr(clients, 'logger'))

        def test_logging_configuration(self):
            ''' Test logging configuration '''
            importlib.reload(clients)
            clients.logger.setLevel.assert_called_once_with("INFO")

    def test_redis_client_initialization(self):
        ''' Test redis client initialization '''
        importlib.reload(clients)
        self.mock_redis.assert_called_once_with(host=self.REDIS_HOST, port=self.REDIS_PORT, decode_responses=True)
        self.assertTrue(hasattr(clients, 'redis_client'))
        self.assertIsInstance(clients.redis_client, self.mock_redis.return_value.__class__)

    def test_logging_initialization(self):
        ''' Test logging initialization '''
        importlib.reload(clients)
        self.mock_logging.assert_called_once_with()
        self.assertTrue(hasattr(clients, 'logger'))
        clients.logger.setLevel.assert_any_call("INFO")
