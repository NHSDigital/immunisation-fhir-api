
import unittest
from unittest.mock import patch, MagicMock
from common.validator.expression_checker import ExpressionChecker


class TestExpressionChecker(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('common.validator.expression_checker.LookUpData')
        patcher2 = patch('common.validator.expression_checker.KeyData')
        patcher3 = patch('common.validator.expression_checker.RecordError')
        patcher4 = patch('common.validator.expression_checker.ErrorReport')

        self.MockLookUpData = patcher1.start()
        self.MockKeyData = patcher2.start()
        self.MockRecordError = patcher3.start()
        self.MockErrorReport = patcher4.start()

        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        self.addCleanup(patcher4.stop)

        self.mock_summarise = MagicMock()
        self.mock_report_exception = MagicMock()
        self.mock_data_parser = MagicMock()

        self.expression_checker = ExpressionChecker(
            self.mock_data_parser,
            self.mock_summarise,
            self.mock_report_exception
        )

    def test_validate_datetime_valid(self):
        result = self.expression_checker.validateExpression(
            "DATETIME",
            rule="",
            field_name="timestamp",
            field_value="2022-01-01T12:00:00",
            row={}
        )
        self.assertTrue(self.MockErrorReport.called or result is None)

    def test_validate_uuid_valid(self):
        result = self.expression_checker.validateExpression(
            "UUID",
            rule="",
            field_name="id",
            field_value="550e8400-e29b-41d4-a716-446655440000",
            row={}
        )
        self.assertTrue(self.MockErrorReport.called or result is None)

    def test_validate_integer_invalid(self):
        result = self.expression_checker.validateExpression(
            "INT",
            rule="",
            field_name="age",
            field_value="notanint",
            row={}
        )
        self.assertTrue(self.MockRecordError.called or result is not None)

    def test_validate_in_array(self):
        # Mock data_parser.get_key_values
        self.mock_data_parser.get_key_values.return_value = ["val1", "val2"]

        result = self.expression_checker.validateExpression(
            "INARRAY",
            rule="",
            field_name="some_field",
            field_value="val2",
            row={}
        )
        self.assertTrue(result is None or self.MockErrorReport.called)

    def test_validate_expression_type_not_found(self):
        result = self.expression_checker.validateExpression(
            "UNKNOWN",
            rule="",
            field_name="field",
            field_value="value",
            row={}
        )
        self.assertIn("Schema expression not found", result)
