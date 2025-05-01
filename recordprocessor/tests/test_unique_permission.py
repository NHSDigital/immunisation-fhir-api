"""Tests for the utils_for_recordprocessor module"""

import unittest

from src.unique_permission import get_unique_action_flags_from_s3
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    ValidMockFileContent,
)


class TestGetUniqueFlagsFromS3(unittest.TestCase):
    def test_get_unique_action_flags_from_s3(self):
        csv_data = ValidMockFileContent.with_new_and_update_and_delete

        # set the expected result
        expected_output = {"NEW", "UPDATE", "DELETE"}
        result = get_unique_action_flags_from_s3(csv_data)
        self.assertEqual(result, expected_output)


if __name__ == "__main__":
    unittest.main()
