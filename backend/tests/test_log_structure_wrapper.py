import unittest
import json
from unittest.mock import patch, MagicMock, ANY
from log_structure import function_info


@patch('log_structure.firehose_logger')
@patch('log_structure.logger')
class TestFunctionInfoWrapper(unittest.TestCase):

    @staticmethod
    def mock_success_function(_event, _context):
        return "Success"

    @staticmethod
    def mock_function_raises(_event, _context):
        raise ValueError("Test error")

    def test_successful_execution(self, mock_logger, mock_firehose_logger):
        # Arrange
        wrapped_function = function_info(self.mock_success_function)
        event = {
            'headers': {
                'X-Correlation-ID': 'test_correlation',
                'X-Request-ID': 'test_request'
            },
            'path': '/test',
            'requestContext': {'resourcePath': '/test'}
        }

        # Act
        result = wrapped_function(event, {})

        # Assert
        self.assertEqual(result, "Success")
        mock_logger.info.assert_called()
        mock_firehose_logger.send_log.assert_called()

        args, kwargs = mock_logger.info.call_args
        logged_info = json.loads(args[0])

        self.assertIn('function_name', logged_info)
        self.assertIn('time_taken', logged_info)
        self.assertEqual(logged_info['X-Correlation-ID'], 'test_correlation')
        self.assertEqual(logged_info['X-Request-ID'], 'test_request')
        self.assertEqual(logged_info['actual_path'], '/test')
        self.assertEqual(logged_info['resource_path'], '/test')

    def test_exception_handling(self, mock_logger, mock_firehose_logger):

        #Act
        decorated_function_raises = function_info(self.mock_function_raises)

        with self.assertRaises(ValueError):
            #Assert
            event = {'headers': {
                'X-Correlation-ID': 'failed_test_correlation',
                'X-Request-ID': 'failed_test_request'
            },
                'path': '/failed_test', 'requestContext': {'resourcePath': '/failed_test'}}
            context = {}
            decorated_function_raises(event, context)

        #Assert
        mock_logger.exception.assert_called()
        mock_firehose_logger.send_log.assert_called()

        args, kwargs = mock_logger.exception.call_args
        logged_info = json.loads(args[0])

        self.assertIn('function_name', logged_info)
        self.assertIn('time_taken', logged_info)
        self.assertEqual(logged_info['X-Correlation-ID'], 'failed_test_correlation')
        self.assertEqual(logged_info['X-Request-ID'], 'failed_test_request')
        self.assertEqual(logged_info['actual_path'], '/failed_test')
        self.assertEqual(logged_info['resource_path'], '/failed_test')
        self.assertEqual(logged_info['error'], str(ValueError("Test error")))