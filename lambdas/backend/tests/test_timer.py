import unittest
from unittest.mock import patch

from timer import timed


class TestTimedDecorator(unittest.TestCase):
    @patch("timer.time")
    @patch("timer.logger")
    def test_timed_logs_correct_execution_time(self, mock_logger, mock_time):
        mock_time.time.side_effect = [1000.0, 1000.12345]

        @timed
        def sample_function():
            return "success"

        result = sample_function()

        self.assertEqual(result, "success")
        mock_logger.info.assert_called_once_with({"time_taken": "sample_function ran in 0.12345s"})

    @patch("timer.time")
    @patch("timer.logger")
    def test_timed_preserves_function_name(self, mock_logger, mock_time):
        mock_time.time.side_effect = [0.0, 0.0]

        @timed
        def my_named_function():
            pass

        my_named_function()

        logged_payload = mock_logger.info.call_args[0][0]
        self.assertIn("my_named_function", logged_payload["time_taken"])
