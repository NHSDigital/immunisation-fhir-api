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
    environment
)

OFFSET = 1  # Days to offset the recorded date by (can be negative)


class TestE2EBatch(unittest.TestCase):
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

        def test_reinstated_success(self):
            """Test REINSTATED scenario."""
            monitor("test_reinstated_success")
            input_file = generate_csv("PHYLIS", "0.5", action_flag="REINSTATED", offset=OFFSET)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "reinstated")
            monitor("test_reinstated_success")

        def test_update_reinstated_success(self):
            """Test UPDATE-REINSTATED scenario."""
            monitor("test_update_reinstated_success")
            input_file = generate_csv("PHYLIS", "0.5", action_flag="UPDATE-REINSTATED", offset=OFFSET)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "update-reinstated")
            monitor("test_update_reinstated_success")

        def test_delete_success(self):
            """Test DELETE scenario."""
            monitor("test_delete_success")
            input_file = generate_csv("PHYLIS", "0.8", action_flag="DELETE", offset=OFFSET)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "DELETE")
            monitor("test_delete_success")
