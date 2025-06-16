import unittest
from unittest.mock import Mock
from event_read import read_event


class TestReadEvent(unittest.TestCase):
    def setUp(self):
        self.mock_redis = Mock()
        self.mock_logger = Mock()

    def test_read_event_success(self):
        self.mock_redis.hgetall.return_value = {"field1": "value1"}
        event = {"read": "myhash"}
        result = read_event(self.mock_redis, event, self.mock_logger)
        self.mock_redis.hgetall.assert_called_once_with("myhash")
        self.assertEqual(result, {"field1": "value1"})

    def test_read_event_missing_key(self):
        event = {"read": ""}
        result = read_event(self.mock_redis, event, self.mock_logger)
        self.assertEqual(result, {"status": "error", "message": "Read key is required."})
        self.mock_redis.hgetall.assert_not_called()

    def test_read_event_exception(self):
        self.mock_redis.hgetall.side_effect = Exception("Redis error")
        event = {"read": "myhash"}
        result = read_event(self.mock_redis, event, self.mock_logger)
        self.assertEqual(result["status"], "error")
        self.assertIn("Error reading key", result["message"])
        self.mock_logger.exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()
