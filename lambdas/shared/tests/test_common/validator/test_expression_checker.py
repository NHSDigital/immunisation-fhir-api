
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import common.validator.enums.exception_messages as ExceptionMessages
from common.validator.expression_checker import ExpressionChecker

# TODO this needs to be expanded to cover all expression types


class TestExpressionChecker(unittest.TestCase):

    def setUp(self):

        self.MockLookUpData = patch(
            'common.validator.expression_checker.LookUpData').start()
        self.MockKeyData = patch(
            'common.validator.expression_checker.KeyData').start()

        self.mock_summarise = MagicMock()
        self.mock_report_exception = MagicMock()
        self.mock_data_parser = MagicMock()

        self.expression_checker = ExpressionChecker(
            self.mock_data_parser,
            self.mock_summarise,
            self.mock_report_exception
        )

    def tearDown(self):
        patch.stopall()

    def test_validate_datetime_valid(self):
        result = self.expression_checker.validate_expression(
            "DATETIME",
            rule="",
            field_name="timestamp",
            field_value="2022-01-01T12:00:00",
            row={}
        )
        self.assertEqual(result.message, "Unexpected exception [ValueError]: Invalid isoformat string: '2022-01-01T12:00:00'")
        self.assertEqual(result.code, ExceptionMessages.UNEXPECTED_EXCEPTION)
        self.assertEqual(result.field, "timestamp")

    def test_validate_uuid_valid(self):
        result = self.expression_checker.validate_expression(
            "UUID",
            rule="",
            field_name="id",
            field_value="550e8400-e29b-41d4-a716-446655440000",
            row={}
        )
        self.assertTrue(result is None)

    def test_validate_integer_invalid(self):
        result = self.expression_checker.validate_expression(
            "INT",
            rule="",
            field_name="age",
            field_value="hello world",
            row={}
        )
        self.assertEqual(result.code, ExceptionMessages.UNEXPECTED_EXCEPTION)
        self.assertEqual(result.field, "age")
        self.assertIn("invalid literal for int()", result.message)

    def test_validate_in_array(self):
        # Mock data_parser.get_key_values
        self.mock_data_parser.get_key_values.return_value = ["val1", "val2"]

        result = self.expression_checker.validate_expression(
            "INARRAY",
            rule="",
            field_name="some_field",
            field_value="val2",
            row={}
        )
        self.assertEqual(result.message, "Value not in array check failed")
        self.assertEqual(result.field, "some_field")

    def test_validate_expression_type_not_found(self):
        result = self.expression_checker.validate_expression(
            "UNKNOWN",
            rule="",
            field_name="field",
            field_value="value",
            row={}
        )
        self.assertIn("Schema expression not found", result)
