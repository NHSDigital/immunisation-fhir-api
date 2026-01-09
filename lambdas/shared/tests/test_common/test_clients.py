import unittest
from unittest.mock import MagicMock, patch

from moto import mock_aws

import common.clients


@mock_aws
class TestClients(unittest.TestCase):
    BUCKET_NAME = "default-bucket"
    AWS_REGION = "eu-west-2"

    def setUp(self):
        # Patch boto3.client
        self.boto3_client_patch = patch("boto3.client", autospec=True)
        self.mock_boto3_client = self.boto3_client_patch.start()

        # Patch logging.getLogger
        self.logging_patch = patch("logging.getLogger", autospec=True)
        self.mock_getLogger = self.logging_patch.start()

        # Patch os.getenv
        self.getenv_patch = patch("os.getenv", autospec=True)
        self.mock_getenv = self.getenv_patch.start()

        # Set environment variable mock return values
        self.mock_getenv.side_effect = lambda key, default=None: {
            "CONFIG_BUCKET_NAME": self.BUCKET_NAME,
            "AWS_REGION": self.AWS_REGION,
        }.get(key, default)

        # Simulate logger instance and patch setLevel
        self.mock_logger_instance = MagicMock()
        self.mock_getLogger.return_value = self.mock_logger_instance

    def tearDown(self):
        self.getenv_patch.stop()
        self.logging_patch.stop()
        self.boto3_client_patch.stop()

    def test_global_s3_client(self):
        """Test global_s3_client is not initialized on import"""
        self.assertEqual(common.clients.global_s3_client, None)

    def test_global_s3_client_initialization(self):
        """Test global_s3_client is initialized exactly once even with multiple invocations"""
        common.clients.get_s3_client()
        self.assertNotEqual(common.clients.global_s3_client, None)
        call_count = self.mock_boto3_client.call_count
        common.clients.get_s3_client()
        self.assertEqual(self.mock_boto3_client.call_count, call_count)

    def test_global_sqs_client(self):
        """Test global_sqs_client is not initialized on import"""
        self.assertEqual(common.clients.global_sqs_client, None)

    def test_global_sqs_client_initialization(self):
        """Test global_sqs_client is initialized exactly once even with multiple invocations"""
        common.clients.get_sqs_client()
        self.assertNotEqual(common.clients.global_sqs_client, None)
        call_count = self.mock_boto3_client.call_count
        common.clients.get_sqs_client()
        self.assertEqual(self.mock_boto3_client.call_count, call_count)
