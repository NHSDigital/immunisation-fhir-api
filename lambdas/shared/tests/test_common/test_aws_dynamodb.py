import unittest
from unittest.mock import patch, MagicMock
from common.aws_dynamodb import get_dynamodb_table


class TestGetIedsTable(unittest.TestCase):

    AWS_REGION = "eu-west-2"  # Add this missing constant

    def setUp(self):
        # Mock the specific logger instance used in the module
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.getenv_patch = patch("os.getenv")
        self.mock_getenv = self.getenv_patch.start()
        self.mock_getenv.side_effect = lambda key, default=None: {
            "AWS_REGION": self.AWS_REGION
        }.get(key, default)

        self.dynamodb_resource_patcher = patch('common.aws_dynamodb.dynamodb_resource')
        self.mock_dynamodb_resource = self.dynamodb_resource_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_ieds_table_success(self):
        # Create a mock table object
        table_name = "abc"
        mock_table = MagicMock()
        self.mock_dynamodb_resource.Table.return_value = mock_table

        # Call the function
        table = get_dynamodb_table(table_name)

        self.mock_dynamodb_resource.Table.assert_called_once_with(table_name)
        self.assertEqual(table, mock_table)
        # Verify the success logging
        self.mock_logger_info.assert_called_once_with("Initializing table: %s", table_name)

    def test_get_ieds_table_failure(self):
        # Simulate exception when accessing Table
        msg = "DynamoDB failure"
        self.mock_dynamodb_resource.Table.side_effect = Exception(msg)
        table_name = "abc"

        with self.assertRaises(Exception) as context:
            get_dynamodb_table(table_name)

        self.assertEqual(str(context.exception), msg)
        # This should now work - mocking the instance method
        self.mock_logger_exception.assert_called_once_with("Error initializing DynamoDB table: %s", table_name)
        # Also verify info logging happened before the exception
        self.mock_logger_info.assert_called_once_with("Initializing table: %s", table_name)
