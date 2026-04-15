import unittest

import models.errors as errors


class TestErrors(unittest.TestCase):
    def test_errors_message_not_successful_error(self):
        """Test correct operation of MessageNotSuccessfulError"""
        test_message = "test_message"

        with self.assertRaises(errors.MessageNotSuccessfulError) as context:
            raise errors.MessageNotSuccessfulError(test_message)
        self.assertEqual(str(context.exception.message), test_message)

    def test_errors_message_not_successful_error_no_message(self):
        """Test correct operation of MessageNotSuccessfulError with no message"""

        with self.assertRaises(errors.MessageNotSuccessfulError) as context:
            raise errors.MessageNotSuccessfulError()
        self.assertIsNone(context.exception.message)

    def test_errors_record_processor_error(self):
        """Test correct operation of RecordProcessorError"""
        test_diagnostics = {"test_diagnostic": "test_value"}

        with self.assertRaises(errors.RecordProcessorError) as context:
            raise errors.RecordProcessorError(test_diagnostics)
        self.assertEqual(context.exception.diagnostics_dictionary, test_diagnostics)
