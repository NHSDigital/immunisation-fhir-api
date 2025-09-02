import unittest

from utils import (
    delete_file_from_s3
)

from constants import (
    SOURCE_BUCKET,
    ACK_BUCKET
)


class TestE2EBatchBase(unittest.TestCase):

    def setUp(self):
        self.uploaded_files = []  # Tracks uploaded input keys
        self.ack_files = []       # Tracks ack keys

    def tearDown(self):
        for file_key in self.uploaded_files:
            delete_file_from_s3(SOURCE_BUCKET, file_key)
        for ack_key in self.ack_files:
            delete_file_from_s3(ACK_BUCKET, ack_key)
