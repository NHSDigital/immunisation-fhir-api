import unittest
from unittest.mock import patch

from timer import timed


class TestTimedDecorator(unittest.TestCase):
    @patch("timer.logger")
    def test_timed_logs_execution_time(self, mock_logger):
        @timed
        def sample_function():
            return "success"

        result = sample_function()
        self.assertEqual(result, "success")

        mock_logger.info.assert_called_once()
