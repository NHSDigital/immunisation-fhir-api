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
)
from per_test import monitor

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    PRE_VALIDATION_ERROR,
    POST_VALIDATION_ERROR,
    FILE_NAME_VAL_ERROR,
    environment
)
from e2e_batch_base import TestE2EBatchBase


@unittest.skipIf(environment == "ref", "if ref")
class TestE2EBatchValidation(TestE2EBatchBase):

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
