import json
import unittest

from sqs_dynamo_utils import _unwrap_dynamodb_value, extract_sqs_imms_data
from test_utils import load_sample_sqs_event


class TestExtractSqsImmsData(unittest.TestCase):
    """
    Test SQS Event extraction utility
    """

    @classmethod
    def setUpClass(cls):
        cls.sample_sqs_event = load_sample_sqs_event()

    def test_extract_sqs_imms_data(self):
        result = extract_sqs_imms_data(self.sample_sqs_event)

        self.assertEqual(result["imms_id"], "d058014c-b0fd-4471-8db9-3316175eb825")
        self.assertEqual(result["supplier_system"], "TPP")
        self.assertEqual(result["vaccine_type"], "hib")
        self.assertEqual(result["operation"], "CREATE")
        self.assertEqual(result["nhs_number"], "9481152782")
        self.assertEqual(result["person_dob"], "20040609")
        self.assertEqual(result["date_and_time"], "20260212T17443700")
        self.assertEqual(result["site_code"], "B0C4P")

    def test_extract_imms_data_field_types(self):
        """Test that extracted fields are the correct types."""
        result = extract_sqs_imms_data(self.sample_sqs_event)

        self.assertIsInstance(result["imms_id"], str)
        self.assertIsInstance(result["supplier_system"], str)
        self.assertIsInstance(result["vaccine_type"], str)
        self.assertIsInstance(result["operation"], str)
        self.assertIsInstance(result["nhs_number"], str)
        self.assertIsInstance(result["person_dob"], str)
        self.assertIsInstance(result["date_and_time"], str)
        self.assertIsInstance(result["site_code"], str)

    def test_extract_imms_data_invalid_json_body(self):
        """Test extraction when body is invalid JSON."""
        event = {"body": "invalid json {"}

        with self.assertRaises(json.JSONDecodeError):
            extract_sqs_imms_data(event)


class TestUnwrapDynamodbValue(unittest.TestCase):
    """Tests for _unwrap_dynamodb_value helper function."""

    def test_unwrap_string_type(self):
        """Test unwrapping DynamoDB String type."""
        value = {"S": "test-value"}
        result = _unwrap_dynamodb_value(value)
        self.assertEqual(result, "test-value")

    def test_unwrap_number_type(self):
        """Test unwrapping DynamoDB Number type."""
        value = {"N": "123"}
        result = _unwrap_dynamodb_value(value)
        self.assertEqual(result, "123")

    def test_unwrap_boolean_type(self):
        """Test unwrapping DynamoDB Boolean type."""
        value = {"BOOL": True}
        result = _unwrap_dynamodb_value(value)
        self.assertTrue(result)

    def test_unwrap_null_type(self):
        """Test unwrapping DynamoDB NULL type."""
        value = {"NULL": True}
        result = _unwrap_dynamodb_value(value)
        self.assertIsNone(result)

    def test_unwrap_map_type(self):
        """Test unwrapping DynamoDB Map type."""
        value = {"M": {"key": {"S": "value"}}}
        result = _unwrap_dynamodb_value(value)
        self.assertEqual(result, {"key": {"S": "value"}})

    def test_unwrap_list_type(self):
        """Test unwrapping DynamoDB List type."""
        value = {"L": [{"S": "item1"}, {"S": "item2"}]}
        result = _unwrap_dynamodb_value(value)
        self.assertEqual(result, [{"S": "item1"}, {"S": "item2"}])
