import unittest
from unittest import skipIf
from utils import (
    generate_csv,
    upload_file_to_s3,
    get_file_content_from_s3,
    wait_for_ack_files,
    check_ack_file_content,
    validate_row_count,
    delete_file_from_s3
)

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    environment
)


class TestE2EBatch(unittest.TestCase):
    def setUp(self):
        self.uploaded_files = []  # Tracks uploaded input keys
        self.ack_files = []       # Tracks ack keys

    def tearDown(self):
        for file_key in self.uploaded_files:
            delete_file_from_s3(SOURCE_BUCKET, file_key)
        for ack_key in self.ack_files:
            delete_file_from_s3(ACK_BUCKET, ack_key)

    @skipIf(environment == "ref", reason="Skip tests in 'ref' environment")
    def test_create_success(self):
        """Test CREATE scenario."""

        # create 3 files to simulate simultaneous uploads
        #  timestamps are in correct sequence
        input_files = generate_files("PHYLIS", "0.3", action_flags=["CREATE", "UPDATE", "DELETE"])

        for input_file in input_files:
            # TODO All 3 files in 1 go
            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

        self.ack_files = wait_for_ack_files(None, input_file)

        for input_file, ack_key in zip(input_files, self.ack_files):
            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "CREATE")


def generate_files(name_prefix, version, action_flags) -> list:
    """Generate multiple CSV files with different action flags."""
    files = []
    for action in action_flags:
        file = generate_csv(name_prefix, version, action_flag=action)
        files.append(file)
    return files
