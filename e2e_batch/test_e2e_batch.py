import unittest

from utils import (
    generate_csv,
    upload_file_to_s3,
    get_file_content_from_s3,
    wait_for_ack_file,
    check_ack_file_content,
    validate_row_count,
)
from per_test import monitor

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    DUPLICATE,
    environment
)
from e2e_batch_base import TestE2EBatchBase


@unittest.skipIf(environment == "ref", "if ref")
class TestE2EBatch(TestE2EBatchBase):

    def test_duplicate_create(self):
        """Test DUPLICATE scenario."""

        monitor("test_duplicate_create")

        input_file = generate_csv("PHYLIS", "0.3", "CREATE",
                                  "RSV", "YGM41",
                                  same_id=True)

        key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
        self.uploaded_files.append(key)

        ack_key = wait_for_ack_file(None, input_file)
        self.ack_files.append(ack_key)

        validate_row_count(input_file, ack_key)

        ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
        check_ack_file_content(ack_content, "Fatal Error", DUPLICATE, "CREATE")

        monitor("test_duplicate_create")

    def test_update_success(self):
        """Test UPDATE scenario."""
        monitor("test_update_success")
        input_file = generate_csv("PHYLIS", "0.5", "UPDATE", "RSV", "YGM41")

        key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
        self.uploaded_files.append(key)

        ack_key = wait_for_ack_file(None, input_file)
        self.ack_files.append(ack_key)

        validate_row_count(input_file, ack_key)

        ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
        check_ack_file_content(ack_content, "OK", None, "UPDATE")
        monitor("test_update_success")

    def test_reinstated_success(self):
        """Test REINSTATED scenario."""
        monitor("test_reinstated_success")
        input_file = generate_csv("PHYLIS", "0.5", "REINSTATED", "RSV", "YGM41")

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
        input_file = generate_csv("PHYLIS", "0.5", "UPDATE-REINSTATED", "RSV", "YGM41")

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
        input_file = generate_csv("PHYLIS", "0.8", "DELETE", "RSV", "YGM41")

        key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
        self.uploaded_files.append(key)

        ack_key = wait_for_ack_file(None, input_file)
        self.ack_files.append(ack_key)

        validate_row_count(input_file, ack_key)

        ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
        check_ack_file_content(ack_content, "OK", None, "DELETE")
        monitor("test_delete_success")
