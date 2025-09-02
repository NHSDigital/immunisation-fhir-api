import unittest

from utils import (
    upload_file_to_s3,
    wait_for_ack_file,
    generate_csv_with_ordered_100000_rows,
    verify_final_ack_file,
)
from per_test import monitor

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    # environment
)
from e2e_batch_base import TestE2EBatchBase


@unittest.skip("Skip all tests")
# @unittest.skipIf(environment != "ref", "if not ref")
class TestE2EBatchRef(TestE2EBatchBase):

    def test_end_to_end_speed_test_with_100000_rows(self):
        monitor("test_end_to_end_speed_test_with_100000_rows")
        """Test end_to_end_speed_test_with_100000_rows scenario with full integration"""
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
