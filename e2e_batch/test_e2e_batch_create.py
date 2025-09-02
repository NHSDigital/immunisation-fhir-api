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
    environment
)
from e2e_batch_base import TestE2EBatchBase


@unittest.skipIf(environment == "ref", "if ref")
class TestE2EBatchCreate(TestE2EBatchBase):

    def test_create_success(self):
        """Test CREATE scenario."""
        monitor("test_create_success")
        input_file = generate_csv("PHYLIS", "0.3", "CREATE",
                                  "RSV", "YGM41")

        key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
        self.uploaded_files.append(key)

        ack_key = wait_for_ack_file(None, input_file)
        self.ack_files.append(ack_key)

        validate_row_count(input_file, ack_key)

        ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
        check_ack_file_content(ack_content, "OK", None, "CREATE")

        monitor("test_create_success")
