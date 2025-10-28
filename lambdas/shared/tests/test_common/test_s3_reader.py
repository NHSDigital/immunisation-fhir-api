import unittest
from unittest.mock import Mock, MagicMock, patch

from common.s3_reader import S3Reader


@patch("common.s3_reader.get_s3_client")
class TestS3Reader(unittest.TestCase):
    def setUp(self):
        self.s3_reader = S3Reader()
        self.bucket = "test-bucket"
        self.key = "test.json"

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.logger_exception_patcher.stop()

    def test_read_success(self, mock_get_s3_client):
        mock_s3 = Mock()
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"foo": "bar"}'
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_get_s3_client.return_value = mock_s3

        result = self.s3_reader.read(self.bucket, self.key)

        self.assertEqual(result, '{"foo": "bar"}')
        mock_s3.get_object.assert_called_once_with(Bucket=self.bucket, Key=self.key)

    def test_read_raises_exception(self, mock_get_s3_client):
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = Exception("S3 error")
        mock_get_s3_client.return_value = mock_s3

        with self.assertRaises(Exception) as context:
            self.s3_reader.read(self.bucket, self.key)

        self.assertIn("S3 error", str(context.exception))
        self.mock_logger_exception.assert_called_once()
