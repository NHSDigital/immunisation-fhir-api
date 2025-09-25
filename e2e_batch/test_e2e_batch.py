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

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    DUPLICATE,
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

    if environment != "ref":
        def test_create_success(self):
            """Test CREATE scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE", offset=1, vax_type="COVID19", ods="8HA94")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "CREATE")

        def test_duplicate_create(self):
            """Test DUPLICATE scenario."""

            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE", same_id=True, offset=2,
                                      vax_type="COVID19", ods="8HA94")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", DUPLICATE, "CREATE")

        def test_update_success(self):
            """Test UPDATE scenario."""
            input_file = generate_csv("PHYLIS", "0.5", action_flag="UPDATE",
                                      offset=3, vax_type="MMR", ods="V0V8L")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "UPDATE")

        def test_reinstated_success(self):
            """Test REINSTATED scenario."""
            input_file = generate_csv("PHYLIS", "0.5",
                                      action_flag="REINSTATED", offset=4,
                                      vax_type="HPV", ods="DPSREDUCED")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "reinstated")
