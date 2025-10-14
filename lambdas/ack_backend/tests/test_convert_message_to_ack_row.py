"""Tests for the ack processor lambda handler."""

import unittest
from unittest.mock import patch

from tests.utils.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from tests.utils.values_for_ack_backend_tests import (
    DefaultValues,
    DiagnosticsDictionaries,
    ValidValues,
)

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from convert_message_to_ack_row import (
        convert_message_to_ack_row,
        get_error_message_for_ack_file,
    )


class TestAckProcessor(unittest.TestCase):
    """Tests for the ack processor lambda handler."""

    def test_get_error_message_for_ack_file(self):
        """Test the get_error_message_for_ack_file function."""
        diagnastics_unclear_error_message = "Unable to determine diagnostics issue"
        server_error_message = "An unhandled error occurred during batch processing"
        sample_diagnostics_message = "Test error message"

        # CASE: no diagnostics
        self.assertEqual(None, get_error_message_for_ack_file(None))

        # CASE: diagnostics is not a dictionary
        self.assertEqual(
            diagnastics_unclear_error_message,
            get_error_message_for_ack_file("not a dict"),
        )

        # CASE: Server error
        self.assertEqual(server_error_message, get_error_message_for_ack_file({"statusCode": 500}))

        # CASE: Diagnostics dictionary missing error_message
        self.assertEqual(
            diagnastics_unclear_error_message,
            get_error_message_for_ack_file({"statusCode": 400}),
        )

        # CASE: Correctly formatted diagnostics dictionary
        self.assertEqual(
            sample_diagnostics_message,
            get_error_message_for_ack_file({"statusCode": 200, "error_message": sample_diagnostics_message}),
        )

    def test_convert_message_to_ack_row(self):
        """Test the convert_message_to_ack_row function."""
        # CASE: Success row
        message = {
            "created_at": DefaultValues.created_at_formatted_string,
            "local_id": DefaultValues.local_id,
            "row_id": DefaultValues.row_id,
            "imms_id": DefaultValues.imms_id,
        }
        self.assertEqual(
            ValidValues.ack_data_success_dict,
            convert_message_to_ack_row(message, DefaultValues.created_at_formatted_string),
        )

        # CASE: Failure row
        message = {
            "created_at": DefaultValues.created_at_formatted_string,
            "local_id": DefaultValues.local_id,
            "row_id": DefaultValues.row_id,
            "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS,
        }
        self.assertEqual(
            {
                **ValidValues.ack_data_failure_dict,
                "OPERATION_OUTCOME": DiagnosticsDictionaries.NO_PERMISSIONS["error_message"],
            },
            convert_message_to_ack_row(message, DefaultValues.created_at_formatted_string),
        )
