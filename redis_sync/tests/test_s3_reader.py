import unittest
from unittest.mock import patch, MagicMock
from s3_reader import S3Reader


class TestS3Reader(unittest.TestCase):
    def setUp(self):
        self.s3_reader = S3Reader()
        self.bucket = "test-bucket"
        self.key = "test.json"

        # Patch s3_client
        self.s3_client_patcher = patch("s3_reader.s3_client")
        self.mock_s3_client = self.s3_client_patcher.start()

        # Patch logger.exception
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

    def tearDown(self):
        self.s3_client_patcher.stop()
        self.logger_exception_patcher.stop()

    def test_read_success(self):
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"foo": "bar"}'
        self.mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = self.s3_reader.read(self.bucket, self.key)

        self.assertEqual(result, '{"foo": "bar"}')
        self.mock_s3_client.get_object.assert_called_once_with(Bucket=self.bucket, Key=self.key)

    def test_read_raises_exception(self):
        self.mock_s3_client.get_object.side_effect = Exception("S3 error")

        with self.assertRaises(Exception) as context:
            self.s3_reader.read(self.bucket, self.key)

        self.assertIn("S3 error", str(context.exception))
        self.mock_logger_exception.assert_called_once()
