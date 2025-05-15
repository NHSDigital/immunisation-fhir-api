import unittest
from tests.utils_for_converter_tests import ValuesForTests
from ConversionChecker import RecordError


MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
    "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
    "SOURCE": "test-source",
}
request_json_data = ValuesForTests.json_data

class TestRecordError(unittest.TestCase):
    def test_fields_and_str(self):
        err = RecordError(
            code=5,
            message="Test failed",
            details="Something went wrong"
        )

        # The attributes should round‑trip
        self.assertEqual(err.code, 5)
        self.assertEqual(err.message, "Test failed")
        self.assertEqual(err.details, "Something went wrong")

        # __repr__ and __str__ both produce the tuple repr
        expected = "(5, 'Test failed', 'Something went wrong')"
        self.assertEqual(str(err),   expected)
        self.assertEqual(repr(err),  expected)

    def test_default_args(self):
        # If you omit arguments they default to None
        err = RecordError()
        self.assertIsNone(err.code)
        self.assertIsNone(err.message)
        self.assertIsNone(err.details)

        # repr shows three Nones
        self.assertEqual(str(err), "(None, None, None)")

if __name__ == "__main__":
    unittest.main()