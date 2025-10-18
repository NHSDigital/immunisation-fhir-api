import importlib
import logging
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import common.clients as clients


class TestClients(unittest.TestCase):
    BUCKET_NAME = "default-bucket"
    AWS_REGION = "eu-west-2"

    def setUp(self):
        # Patch boto3.client
        self.boto3_client_patch = patch("boto3.client", autospec=True)
        self.mock_boto3_client = self.boto3_client_patch.start()
        self.addCleanup(self.boto3_client_patch.stop)

        # Patch logging.getLogger
        self.logging_patch = patch("logging.getLogger", autospec=True)
        self.mock_getLogger = self.logging_patch.start()
        self.addCleanup(self.logging_patch.stop)

        # Patch os.getenv
        self.getenv_patch = patch("os.getenv", autospec=True)
        self.mock_getenv = self.getenv_patch.start()
        self.addCleanup(self.getenv_patch.stop)

        # Set environment variable mock return values
        self.mock_getenv.side_effect = lambda key, default=None: {
            "CONFIG_BUCKET_NAME": self.BUCKET_NAME,
            "AWS_REGION": self.AWS_REGION,
        }.get(key, default)

        # Simulate logger instance and patch setLevel
        self.mock_logger_instance = MagicMock()
        self.mock_getLogger.return_value = self.mock_logger_instance

        # Reload the module under test to apply patches
        importlib.reload(clients)

    def test_env_variables_loaded(self):
        """Test that environment variables are loaded correctly"""
        self.assertEqual(clients.CONFIG_BUCKET_NAME, self.BUCKET_NAME)
        self.assertEqual(clients.REGION_NAME, self.AWS_REGION)

    def test_boto3_client_created_for_s3(self):
        """Test that S3 boto3 client is created with correct region"""
        self.mock_boto3_client.assert_any_call("s3", region_name=self.AWS_REGION)

    def test_boto3_client_created_for_firehose(self):
        """Test that Firehose boto3 client is created with correct region"""
        self.mock_boto3_client.assert_any_call("firehose", region_name=self.AWS_REGION)

    def test_logger_is_initialized(self):
        """Test that a logger instance is initialized"""
        self.mock_getLogger.assert_called_once_with()
        self.assertTrue(hasattr(clients, "logger"))

    def test_logger_set_level(self):
        """Test that logger level is set to INFO"""
        self.mock_logger_instance.setLevel.assert_called_once_with(logging.INFO)

    def test_global_s3_client(self):
        """Test global_s3_client is not initialized on import"""
        importlib.reload(clients)
        self.assertEqual(clients.global_s3_client, None)

    def test_global_s3_client_initialization(self):
        """Test global_s3_client is initialized exactly once even with multiple invocations"""
        importlib.reload(clients)
        clients.get_s3_client()
        self.assertNotEqual(clients.global_s3_client, None)
        call_count = self.mock_boto3_client.call_count
        clients.get_s3_client()
        self.assertEqual(self.mock_boto3_client.call_count, call_count)
