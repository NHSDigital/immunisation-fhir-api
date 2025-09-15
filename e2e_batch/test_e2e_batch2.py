import unittest
import time
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

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    PRE_VALIDATION_ERROR,
    POST_VALIDATION_ERROR,
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

        def test_update_reinstated_success(self):
            """Test UPDATE-REINSTATED scenario."""
            input_file = generate_csv("PHYLIS", "0.5",
                                      action_flag="UPDATE-REINSTATED", offset=5,
                                      vax_type="MENACWY", ods="DPSFULL")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "update-reinstated")

        def test_delete_success(self):
            """Test DELETE scenario."""
            input_file = generate_csv("PHYLIS", "0.8",
                                      action_flag="DELETE", offset=6,
                                      vax_type="MMR", ods="V0V8L")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "DELETE")

        def test_pre_validation_error(self):
            """Test PRE-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "TRUE", action_flag="CREATE",
                                      offset=7, vax_type="MMR", ods="X8E5B")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            validate_row_count(input_file, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", PRE_VALIDATION_ERROR, None)

        def test_post_validation_error(self):
            """Test POST-VALIDATION error scenario."""
            input_file = generate_csv("", "0.3", action_flag="CREATE",
                                      offset=8, vax_type="3IN1", ods="YGJ")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(None, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", POST_VALIDATION_ERROR, None)

        def test_file_name_validation_error(self):
            """Test FILE-NAME-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE",
                                      file_key=True, offset=9,
                                      vax_type="HPV", ods="YGA")
            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

        def test_header_name_validation_error(self):
            """Test HEADER-NAME-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE",
                                      headers="NH_NUMBER", offset=10,
                                      vax_type="3IN1", ods="YGMYW")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

        # This test updates the permissions_config.json file from the imms-internal-dev-supplier-config
        # S3 bucket shared across multiple environments (PR environments, internal-dev, int, and ref).
        # Running this may modify permissions in these environments, causing unintended side effects.
        @unittest.skip("Modifies shared S3 permissions configuration")
        def test_invalid_permission(self):
            """Test INVALID-PERMISSION error scenario."""
            upload_config_file("MMR_FULL")  # permissions_config.json is updated here
            time.sleep(20)

            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE",
                                      offset=11, vax_type="PINNACLE", ods="8J1100001")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            ack_key = wait_for_ack_file(True, input_file)
            self.ack_files.append(ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

            upload_config_file("COVID19_FULL")
            time.sleep(20)

    else:
        def test_end_to_end_speed_test_with_100000_rows(self):
            """Test end_to_end_speed_test_with_100000_rows scenario with full integration"""
            input_file = generate_csv_with_ordered_100000_rows(12,
                                                               vax_type="COVID19", ods="DPSFULL")

            key = upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            self.uploaded_files.append(key)

            final_ack_key = wait_for_ack_file(None, input_file, timeout=1800)
            self.ack_files.append(final_ack_key)

            response = verify_final_ack_file(final_ack_key)
            assert response is True


if __name__ == "__main__":
    unittest.main()
