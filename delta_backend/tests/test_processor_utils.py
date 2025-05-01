
import unittest
from helpers.processor_utils import get_op_outcome


class TestGetOpOutcome(unittest.TestCase):
    def test_get_op_outcome_basic(self):
        # Arrange
        status_code = 200
        status_desc = "Operation successful"

        # Act
        outcome = get_op_outcome(status_code, status_desc)

        # Assert
        self.assertEqual(outcome["statusCode"], "200")
        self.assertEqual(outcome["statusDesc"], "Operation successful")
        self.assertNotIn("diagnostics", outcome)
        self.assertNotIn("record", outcome)
        self.assertNotIn("operation_type", outcome)

    def test_get_op_outcome_with_diagnostics(self):
        # Arrange
        status_code = 500
        status_desc = "Operation failed"
        diagnostics = "An error occurred during processing"

        # Act
        outcome = get_op_outcome(status_code, status_desc, diagnostics=diagnostics)

        # Assert
        self.assertEqual(outcome["statusCode"], "500")
        self.assertEqual(outcome["statusDesc"], "Operation failed")
        self.assertEqual(outcome["diagnostics"], "An error occurred during processing")
        self.assertNotIn("record", outcome)
        self.assertNotIn("operation_type", outcome)

    def test_get_op_outcome_with_record(self):
        # Arrange
        status_code = 200
        status_desc = "Record processed successfully"
        record = "12345"

        # Act
        outcome = get_op_outcome(status_code, status_desc, record=record)

        # Assert
        self.assertEqual(outcome["statusCode"], "200")
        self.assertEqual(outcome["statusDesc"], "Record processed successfully")
        self.assertEqual(outcome["record"], "12345")
        self.assertNotIn("diagnostics", outcome)
        self.assertNotIn("operation_type", outcome)

    def test_get_op_outcome_with_operation_type(self):
        # Arrange
        status_code = 200
        status_desc = "Operation completed"
        operation_type = "CREATE"

        # Act
        outcome = get_op_outcome(status_code, status_desc, operation_type=operation_type)

        # Assert
        self.assertEqual(outcome["statusCode"], "200")
        self.assertEqual(outcome["statusDesc"], "Operation completed")
        self.assertEqual(outcome["operation_type"], "CREATE")
        self.assertNotIn("diagnostics", outcome)
        self.assertNotIn("record", outcome)

    def test_get_op_outcome_with_all_fields(self):
        # Arrange
        status_code = 207
        status_desc = "Partial success"
        diagnostics = "Some records failed"
        record = "67890"
        operation_type = "UPDATE"

        # Act
        outcome = get_op_outcome(
            status_code, status_desc, diagnostics=diagnostics, record=record, operation_type=operation_type
        )

        # Assert
        self.assertEqual(outcome["statusCode"], "207")
        self.assertEqual(outcome["statusDesc"], "Partial success")
        self.assertEqual(outcome["diagnostics"], "Some records failed")
        self.assertEqual(outcome["record"], "67890")
        self.assertEqual(outcome["operation_type"], "UPDATE")