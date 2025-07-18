import unittest
from unittest.mock import patch
import common.clients as clients
import importlib


class TestClients(unittest.TestCase):

    BUCKET_NAME = "default-bucket"
    AWS_REGION = "eu-west-2"

    def setUp(self):
        self.boto3_client_patch = patch("boto3.client")
        self.mock_boto3_client = self.boto3_client_patch.start()
        self.logging_patch = patch("logging.getLogger")
        self.mock_logging = self.logging_patch.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.getenv_patch = patch("os.getenv")
        self.mock_getenv = self.getenv_patch.start()
        self.mock_getenv.side_effect = lambda key, default=None: {
            "CONFIG_BUCKET_NAME": self.BUCKET_NAME,
            "AWS_REGION": self.AWS_REGION
        }.get(key, default)

        self.mock_boto3_client.return_value = self.mock_boto3_client
        self.mock_boto3_client.return_value.send_message = {}

    def tearDown(self):
        patch.stopall()

    def test_os_environ(self):
        # Test if environment variables are set correctly
        importlib.reload(clients)
        self.assertEqual(clients.CONFIG_BUCKET_NAME, self.BUCKET_NAME)
        self.assertEqual(clients.REGION_NAME, self.AWS_REGION)

    def test_boto3_client(self):
        ''' Test boto3 client is created with correct parameters '''
        importlib.reload(clients)
        self.mock_boto3_client.assert_any_call("s3", region_name=self.AWS_REGION)

    def test_firehose_client(self):
        ''' Test firehose client is created with correct parameters '''
        importlib.reload(clients)
        self.mock_boto3_client.assert_any_call("firehose", region_name=self.AWS_REGION)

    def test_logging_setup(self):
        ''' Test logging is set up correctly '''
        importlib.reload(clients)
        self.assertTrue(hasattr(clients, 'logger'))

    def test_logging_configuration(self):
        ''' Test logging configuration '''
        importlib.reload(clients)
        clients.logger.setLevel.assert_called_once_with("INFO")

    def test_logging_initialization(self):
        ''' Test logging initialization '''
        importlib.reload(clients)
        self.mock_logging.assert_called_once_with()
        self.assertTrue(hasattr(clients, 'logger'))
        clients.logger.setLevel.assert_any_call("INFO")
