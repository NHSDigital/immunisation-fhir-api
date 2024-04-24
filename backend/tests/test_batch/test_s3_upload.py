import unittest
from unittest.mock import MagicMock

from batch.report import S3FixedBufferStream


class TestS3FixedBufferStream(unittest.TestCase):
    def setUp(self):
        self.s3_client = MagicMock()
        self.bucket = "a_bucket"
        self.key = "a_key"
        self.s3_upload = S3FixedBufferStream(s3_client=self.s3_client, bucket=self.bucket, key=self.key)

    def test_add_data(self):
        """it should add data to the buffer"""

        data = b"some data"
        self.s3_upload.add_data(data)

        self.assertEqual(self.s3_upload.stream.getvalue(), data)

    def test_close(self):
        """it should upload the buffer to S3"""

        self.s3_upload.stream.write(b"some data")
        self.s3_upload.close()

        self.s3_client.upload_fileobj.assert_called_once_with(self.s3_upload.stream, self.bucket, self.key)

    def test_close_stream(self):
        """it should close the stream"""

        self.s3_upload.stream = MagicMock()
        self.s3_upload.close()

        self.s3_upload.stream.close.assert_called_once()
