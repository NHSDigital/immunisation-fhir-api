import unittest
from unittest.mock import patch, MagicMock
from src.delta import handler
import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


class DeltaTestCase(unittest.TestCase):

    @patch("src.delta.firehose_logger")  # Mock the firehose_logger instance in delta.py
    def test_handler(self, mock_firehose_logger):
        """ it should handle delta event """
        
        logger.info("Test delta.handler")
        
        event = {"text": "hello world"}

        # Mock the send_log method
        mock_firehose_logger.send_log = MagicMock()

        # Act
        result = handler(event, None)

        # Assert
        # Check the handler's response
        self.assertEqual(result["statusCode"], 200)

        # Verify that send_log was called with the correct event
        mock_firehose_logger.send_log.assert_called_once_with(event)