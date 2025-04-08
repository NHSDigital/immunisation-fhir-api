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
)
from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    PRE_VALIDATION_ERROR,
    POST_VALIDATION_ERROR,
    DUPLICATE,
    FILE_NAME_VAL_ERROR,
    env_value,
    env_internal_dev,
)


@unittest.skipIf(env_internal_dev, "TestE2EBatch for internal-dev environment")
class TestE2EBatch(unittest.TestCase):

    if env_value != "ref":

        def test_create_success(self):
            """Test CREATE scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "CREATE")

        def test_duplicate_create(self):
            """Test DUPLICATE scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE", same_id=True)
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", DUPLICATE, "CREATE")

        def test_update_success(self):
            """Test UPDATE scenario."""
            input_file = generate_csv("PHYLIS", "0.5", action_flag="UPDATE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "UPDATE")

        def test_reinstated_success(self):
            """Test REINSTATED scenario."""
            input_file = generate_csv("PHYLIS", "0.5", action_flag="REINSTATED")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "reinstated")

        def test_update_reinstated_success(self):
            """Test UPDATE-REINSTATED scenario."""
            input_file = generate_csv("PHYLIS", "0.5", action_flag="UPDATE-REINSTATED")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "update-reinstated")

        def test_delete_success(self):
            """Test DELETE scenario."""
            input_file = generate_csv("PHYLIS", "0.8", action_flag="DELETE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "DELETE")

        def test_pre_validation_error(self):
            """Test PRE-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "TRUE", action_flag="CREATE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            validate_row_count(input_file, ack_key)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", PRE_VALIDATION_ERROR, None)

        def test_post_validation_error(self):
            """Test POST-VALIDATION error scenario."""
            input_file = generate_csv("", "0.3", action_flag="CREATE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(None, input_file)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Fatal Error", POST_VALIDATION_ERROR, None)

        def test_file_name_validation_error(self):
            """Test FILE-NAME-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE", file_key=True)
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(True, input_file)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

        def test_header_name_validation_error(self):
            """Test HEADER-NAME-VALIDATION error scenario."""
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE", headers="NH_NUMBER")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(True, input_file)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)

        def test_invalid_permission(self):
            """Test INVALID-PERMISSION error scenario."""
            upload_config_file("MMR_FULL")
            time.sleep(20)
            input_file = generate_csv("PHYLIS", "0.3", action_flag="CREATE")
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            ack_key = wait_for_ack_file(True, input_file)
            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "Failure", FILE_NAME_VAL_ERROR, None)
            upload_config_file("COVID19_FULL")
            time.sleep(20)

    else:

        def test_end_to_end_speed_test_with_100000_rows(self):
            """Test end_to_end_speed_test_with_100000_rows scenario with full integration"""
            input_file = generate_csv_with_ordered_100000_rows(None)
            upload_file_to_s3(input_file, SOURCE_BUCKET, INPUT_PREFIX)
            final_ack_key = wait_for_ack_file(None, input_file, timeout=1800)
            response = verify_final_ack_file(final_ack_key)
            assert response is True


if __name__ == "__main__":
    unittest.main()
