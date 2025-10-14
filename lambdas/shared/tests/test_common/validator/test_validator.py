import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import common.validator.enums.error_levels as ErrorLevels
from common.validator.record_error import ErrorReport
from common.validator.validator import DataType
from common.validator.validator import Validator


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.mock_expression_checker = patch('common.validator.validator.ExpressionChecker').start()
        self.mock_schema_parser = patch('common.validator.validator.SchemaParser').start()
        self.mock_fhir_parser = patch('common.validator.validator.FHIRParser').start()
        self.mock_csv_parser = patch('common.validator.validator.CSVParser').start()
        self.mock_csv_line_parser = patch('common.validator.validator.CSVLineParser').start()

    def tearDown(self):
        patch.stopall()

    def test_run_validation_csv(self):
        # Setup mocks
        self.mock_csv_parser.parse_csv_file.return_value = None
        self.mock_schema_parser.parse_schema.return_value = None
        self.mock_schema_parser.getExpressions.return_value = [
            {'fieldNameCSV': 'test_field', 'expressionId': 'exp1', 'errorLevel': 1,
             'expression': {'expressionName': 'Test', 'expressionType': 'type', 'expressionRule': 'rule'},
             'errorGroup': 'group'}
        ]
        self.mock_expression_checker.return_value.validate_expression.return_value = None

        validator = Validator()
        result = validator.validate_csv('file.csv')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_run_validation_fhir_exception(self):
        # Simulate exception in FHIRParser
        self.mock_fhir_parser.side_effect = Exception("FHIR error")
        validator = Validator()
        result = validator.validate_fhir('file.fhir')
        self.assertIsInstance(result, list)
        self.assertEqual(result[0].code, 0)
        self.assertIn('Data Parser Unexpected exception', result[0].message)

    def test_run_validation_schema_exception(self):
        # Simulate exception in SchemaParser
        self.mock_fhir_parser.return_value.parse_fhir_file.return_value = None
        self.mock_schema_parser.side_effect = Exception("Schema error")
        validator = Validator()
        result = validator.validate_fhir('file.fhir')
        self.assertIsInstance(result, list)
        self.assertEqual(result[0].code, 0)
        self.assertIn('Schema Parser Unexpected exception', result[0].message)

    def test_run_validation_expression_checker_exception(self):
        # Simulate exception in ExpressionChecker
        self.mock_fhir_parser.return_value.parse_fhir_file.return_value = None
        self.mock_schema_parser.return_value.parse_schema.return_value = None
        self.mock_schema_parser.return_value.get_expressions.return_value = []
        self.mock_expression_checker.side_effect = Exception("ExpressionChecker error")
        validator = Validator()
        result = validator.validate_fhir('file.fhir')
        self.assertIsInstance(result, list)
        self.assertEqual(result[0].code, 0)
        self.assertIn('Expression Checker Unexpected exception', result[0].message)

    def test_run_validation_expression_getter_exception(self):
        # Simulate exception in getExpressions
        self.mock_fhir_parser.return_value.parse_fhir_file.return_value = None
        self.mock_schema_parser.return_value.parse_schema.return_value = None
        self.mock_schema_parser.return_value.get_expressions.side_effect = Exception("Expressions error")
        self.mock_expression_checker.return_value = MagicMock()
        validator = Validator()
        result = validator.validate_fhir('file.fhir')
        self.assertIsInstance(result, list)
        self.assertEqual(result[0].code, 0)
        self.assertIn('Expression Getter Unexpected exception', result[0].message)

    @patch('common.validator.validator.DQReporter')
    def test_build_error_report(self, mock_dq_reporter):
        mock_dq_reporter.return_value.generate_error_report.return_value = {'report': 'ok'}
        validator = Validator(data_type=DataType.CSV, filepath='file.csv')
        validator.data_parser = MagicMock()
        validator.data_parser.get_key_single_value.return_value = '2023-01-01'
        result = validator.build_error_report('event123')
        self.assertEqual(result, {'report': 'ok'})
        mock_dq_reporter.return_value.generate_error_report.assert_called_once()

    def test_has_validation_failed_true(self):
        v = Validator(data_type=DataType.CSV)
        v.error_records.append(ErrorReport(error_level=ErrorLevels.CRITICAL_ERROR))  # Assuming 2 is CRITICAL_ERROR
        self.assertTrue(v.has_validation_failed())

    def test_has_validation_failed_false(self):
        v = Validator(data_type=DataType.CSV)
        v.error_records.append(ErrorReport(error_level=ErrorLevels.WARNING))
        self.assertFalse(v.has_validation_failed())
