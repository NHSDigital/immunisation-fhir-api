import time
import unittest
from utils import (
    generate_csv,
    upload_file_to_s3,
    get_file_content_from_s3,
    wait_for_ack_file,
    check_ack_file_content,
    validate_row_count,
    upload_config_file,
    generate_csv_with_ordered_100000_rows,
    verify_final_ack_file,
    delete_file_from_s3
)
from per_test import monitor

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    PRE_VALIDATION_ERROR,
    POST_VALIDATION_ERROR,
    DUPLICATE,
    FILE_NAME_VAL_ERROR,
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
            monitor("test_create_success")
            input_file = generate_csv("PHYLIS", "0.3",
                                      "RSV", "YGM41",
                                      action_flag="CREATE")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "CREATE")

            monitor("test_create_success")

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

        def test_pre_validation_error(self):
            """Test PRE-VALIDATION error scenario."""
            monitor("test_pre_validation_error")
            input_file = generate_csv("PHYLIS", "TRUE", "CREATE", "RSV", "YGM41")

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
            input_file = generate_csv("", "0.3", "CREATE", "RSV", "YGM41")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", POST_VALIDATION_ERROR, None)
            monitor("test_post_validation_error")

        def test_file_name_validation_error(self):
            """Test FILE-NAME-VALIDATION error scenario."""
            monitor("test_file_name_validation_error")
            input_file = generate_csv("PHYLIS", "0.3", "CREATE", "RSV", "YGM41", file_key=True)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)
            monitor("test_file_name_validation_error")

        def test_header_name_validation_error(self):
            """Test HEADER-NAME-VALIDATION error scenario."""
            monitor("test_header_name_validation_error")
            input_file = generate_csv("PHYLIS", "0.3", "CREATE", "RSV", "YGM41", headers="NH_NUMBER")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)
            monitor("test_header_name_validation_error")

        # This test updates the permissions_config.json file from the imms-internal-dev-supplier-config
        # S3 bucket shared across multiple environments (PR environments, internal-dev, int, and ref).
        # Running this may modify permissions in these environments, causing unintended side effects.
        @unittest.skip("Modifies shared S3 permissions configuration")
        def test_invalid_permission(self):
            """Test INVALID-PERMISSION error scenario."""
            monitor("test_invalid_permission")
            upload_config_file("MMR_FULL")  # permissions_config.json is updated here
            time.sleep(20)

            input_file = generate_csv("PHYLIS", "0.3", "CREATE", "RSV", "YGM41")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

            upload_config_file("COVID19_FULL")
            time.sleep(20)
            monitor("test_invalid_permission")

    else:
        def test_end_to_end_speed_test_with_100000_rows(self):
            monitor("test_end_to_end_speed_test_with_100000_rows")
            """Test end_to_end_speed_test_with_100000_rows scenario with full integration"""
            file_name = f"RSV_Vaccinations_v5_YGM41_{timestamp}.csv" if not file_name else file_name
            input_file = generate_csv_with_ordered_100000_rows(None)

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            final_ack_key = wait_for_ack_file(None, input_file, timeout=1800)
            self.ack_files.append(final_ack_key)

            response = verify_final_ack_file(final_ack_key)
            assert response is True
            monitor("test_end_to_end_speed_test_with_100000_rows")


if __name__ == "__main__":
    unittest.main()
