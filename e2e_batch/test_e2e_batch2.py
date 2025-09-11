import unittest
from utils import (
    generate_csv,
    upload_file_to_s3,
    get_file_content_from_s3,
    wait_for_ack_file,
    check_ack_file_content,
    validate_row_count,
    delete_file_from_s3
)
from per_test import monitor

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    PRE_VALIDATION_ERROR,
    POST_VALIDATION_ERROR,
    environment
)

OFFSET = 2


class TestE2EBatch2(unittest.TestCase):

    def setUp(self):
        self.uploaded_files = []  # Tracks uploaded input keys
        self.ack_files = []       # Tracks ack keys

    def tearDown(self):
        # get name of unit test
        unit_test_name = self._testMethodName
        marker = f"tearDown-{unit_test_name}"

        monitor(marker, is_test=False)
        for file_key in self.uploaded_files:
            delete_file_from_s3(SOURCE_BUCKET, file_key)
        for ack_key in self.ack_files:
            delete_file_from_s3(ACK_BUCKET, ack_key)
        monitor(marker, is_test=False)

    if environment != "ref":

        def test_pre_validation_error(self):
            """Test PRE-VALIDATION error scenario."""
            monitor("test_pre_validation_error")
            input_file = generate_csv("PHYLIS", "TRUE", action_flag="CREATE", offset=OFFSET)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", PRE_VALIDATION_ERROR, None)
            monitor("test_pre_validation_error")

        def test_post_validation_error(self):
            """Test POST-VALIDATION error scenario."""
            monitor("test_post_validation_error")
            input_file = generate_csv("", "0.3", action_flag="CREATE", offset=OFFSET)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", POST_VALIDATION_ERROR, None)
            monitor("test_post_validation_error")
