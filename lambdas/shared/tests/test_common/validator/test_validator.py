import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.common.validator.validator import Validator

from common.validator.constants.enums import DataType, ErrorLevels, ExceptionLevels
from common.validator.error_report.record_error import ErrorReport
from tests.test_common.validator.testing_utils.constants import CSV_VALUES
from tests.test_common.validator.testing_utils.csv_fhir_utils import parse_test_file


class TestValidator(unittest.TestCase):
    def setUp(self):
        """Setup shared test data for all test cases."""
        validation_folder = Path(__file__).resolve().parent
        self.FHIRFilePath = validation_folder / "sample_data/vaccination.json"
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.SchemaFile = parse_test_file(self.schemaFilePath)
        self.fhir_resources = parse_test_file(self.FHIRFilePath)
        self.csv_row = CSV_VALUES

    def test_validate_csv(self):
        """Ensure CSV validation runs successfully without errors."""
        validator = Validator(self.SchemaFile)
        result = validator.validate_csv_row(self.csv_row)

        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(err, ErrorReport) for err in result))
        print(f"CSV Validation Errors: {result}")
        self.assertEqual(len(result), 0, "Expected no validation errors for valid CSV row")

    def test_has_validation_failed_detects_critical_error(self):
        """Ensure has_validation_failed returns True when critical errors are present."""
        error_records = [ErrorReport(code=1, message="Critical issue", error_level=ErrorLevels.CRITICAL_ERROR)]
        validator = Validator()
        self.assertTrue(validator.has_validation_failed(error_records))

    import unittest


class TestValidateFHIR(unittest.TestCase):
    def setUp(self):
        """Common setup for all validate_fhir tests."""
        self.validator = Validator(schema_file="dummy_schema.json")
        self.fhir_data = {"recorded": "2025-01-10T10:00:00Z"}

    @patch.object(Validator, "run_validation")
    def test_validate_fhir_calls_run_validation_with_correct_params(self, mock_run_validation):
        """Ensure validate_fhir calls run_validation with correct arguments."""
        mock_run_validation.return_value = [ErrorReport(code=1, message="ok")]

        result = self.validator.validate_fhir(self.fhir_data)

        mock_run_validation.assert_called_once_with(
            data_type=DataType.FHIR,
            fhir_data=self.fhir_data,
            summarise=False,
            report_unexpected_exception=True,
            inc_header_in_row_count=True,
        )

        self.assertEqual(result, mock_run_validation.return_value)
        self.assertIsInstance(result[0], ErrorReport)

    @patch.object(Validator, "run_validation")
    def test_validate_fhir_passes_flags_correctly(self, mock_run_validation):
        """Ensure validate_fhir passes all optional flags properly."""
        self.validator.validate_fhir(
            self.fhir_data,
            summarise=True,
            report_unexpected_exception=False,
            inc_header_in_row_count=False,
        )

        mock_run_validation.assert_called_once_with(
            data_type=DataType.FHIR,
            fhir_data=self.fhir_data,
            summarise=True,
            report_unexpected_exception=False,
            inc_header_in_row_count=False,
        )

    @patch.object(Validator, "run_validation")
    def test_validate_fhir_returns_empty_list_on_no_errors(self, mock_run_validation):
        """Ensure validate_fhir returns empty list when there are no validation errors."""
        mock_run_validation.return_value = []

        result = self.validator.validate_fhir(self.fhir_data)

        self.assertEqual(result, [])
        mock_run_validation.assert_called_once()


class TestValidateCSVRow(unittest.TestCase):
    def setUp(self):
        """Common setup for CSV row validation tests."""
        self.validator = Validator(schema_file="dummy_schema.json")
        self.csv_row = {"nhs_number": "1234567890", "recorded": "2025-01-10"}

    @patch.object(Validator, "run_validation")
    def test_validate_csv_row_calls_run_validation_with_correct_params(self, mock_run_validation):
        """Ensure validate_csv_row calls run_validation with correct arguments."""
        mock_run_validation.return_value = [ErrorReport(code=1, message="ok")]

        result = self.validator.validate_csv_row(self.csv_row)

        mock_run_validation.assert_called_once_with(
            data_type=DataType.CSVROW,
            csv_row=self.csv_row,
            summarise=False,
            report_unexpected_exception=True,
            inc_header_in_row_count=True,
        )

        self.assertEqual(result, mock_run_validation.return_value)
        self.assertIsInstance(result[0], ErrorReport)

    @patch.object(Validator, "run_validation")
    def test_validate_csv_row_passes_flags_correctly(self, mock_run_validation):
        """Ensure validate_csv_row passes optional flags correctly."""
        self.validator.validate_csv_row(
            self.csv_row,
            summarise=True,
            report_unexpected_exception=False,
            inc_header_in_row_count=False,
        )

        mock_run_validation.assert_called_once_with(
            data_type=DataType.CSVROW,
            csv_row=self.csv_row,
            summarise=True,
            report_unexpected_exception=False,
            inc_header_in_row_count=False,
        )

    @patch.object(Validator, "run_validation")
    def test_validate_csv_row_returns_empty_list_on_no_errors(self, mock_run_validation):
        """Ensure validate_csv_row returns empty list when validation succeeds."""
        mock_run_validation.return_value = []

        result = self.validator.validate_csv_row(self.csv_row)

        self.assertEqual(result, [])
        mock_run_validation.assert_called_once()


class TestRunValidation(unittest.TestCase):
    def setUp(self):
        """Shared setup."""
        self.validator = Validator(schema_file="test_schema.json")
        self.fhir_data = {"recorded": "2025-01-10T10:00:00Z"}
        self.csv_row = {"nhs_number": "1234567890", "recorded": "2025-01-10"}

    @patch("src.common.validator.validator.FHIRInterface")
    @patch("src.common.validator.validator.SchemaParser.parse_schema")
    @patch("src.common.validator.validator.ExpressionChecker")
    def test_run_validation_fhir_success(self, mock_expr_checker, mock_schema_parser, mock_fhir_interface):
        """Ensure successful FHIR validation completes and returns empty error list."""
        mock_schema = MagicMock()
        mock_schema.get_expressions.return_value = [
            {
                "fieldNameFHIR": "recorded",
                "expression": {"expressionName": "Check", "expressionType": "LEN", "expressionRule": ">0"},
                "expressionId": "1",
                "errorLevel": 1,
                "errorGroup": "completeness",
            }
        ]
        mock_schema_parser.return_value = mock_schema
        mock_expr_checker.return_value = MagicMock()
        mock_fhir_interface.return_value = MagicMock()

        with patch.object(self.validator, "_validate_expression", return_value=None) as mock_validate:
            result = self.validator.run_validation(DataType.FHIR, fhir_data=self.fhir_data)
            mock_validate.assert_called_once()
            self.assertEqual(result, [])

    @patch("src.common.validator.validator.FHIRInterface", side_effect=Exception("Parser init failed"))
    def test_run_validation_parser_failure(self, mock_fhir_interface):
        """Return ErrorReport if FHIR parser creation fails."""
        result = self.validator.run_validation(DataType.FHIR, fhir_data=self.fhir_data)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ErrorReport)
        self.assertIn("Data Parser Unexpected exception", result[0].message)

    @patch("src.common.validator.validator.SchemaParser.parse_schema", side_effect=Exception("Schema load error"))
    @patch("src.common.validator.validator.FHIRInterface")
    def test_run_validation_schema_parse_failure(self, mock_fhir_interface, mock_parse_schema):
        """Return ErrorReport if schema parsing fails."""
        mock_fhir_interface.return_value = MagicMock()
        result = self.validator.run_validation(DataType.FHIR, fhir_data=self.fhir_data)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ErrorReport)
        self.assertIn("Schema Parser Unexpected exception", result[0].message)


class TestValidateExpression(unittest.TestCase):
    def setUp(self):
        self.validator = Validator(schema_file="dummy_schema.json")
        self.expression = {
            "expressionId": "EXP1",
            "fieldNameFHIR": "recorded",
            "fieldNameFlat": "RECORDED_DATE",
            "errorLevel": 1,
            "expression": {
                "expressionName": "Check Recorded Date",
                "expressionType": "NOTEMPTY",
                "expressionRule": "",
            },
            "errorGroup": "core",
        }


def test_extracts_correct_field_based_on_data_format(self):
    mock_expr_checker = MagicMock()
    mock_expr_checker.validate_expression.return_value = None

    # Batch parser mock
    batch_parser = MagicMock()
    batch_parser.get_data_format.return_value = "batch"
    batch_parser.extract_field_values.return_value = ["2025-01-10"]

    # FHIR parser mock
    fhir_parser = MagicMock()
    fhir_parser.get_data_format.return_value = "fhir"
    fhir_parser.extract_field_values.return_value = ["2025-01-10T10:00:00Z"]

    # Batch path
    self.validator._validate_expression(mock_expr_checker, self.expression, batch_parser, [], True)
    batch_parser.extract_field_values.assert_called_once_with("RECORDED_DATE")

    # FHIR path
    self.validator._validate_expression(mock_expr_checker, self.expression, fhir_parser, [], True)
    fhir_parser.extract_field_values.assert_called_once_with("recorded")


@patch("src.common.validator.validator.add_error_record")
def test_handles_extract_field_values_exception(self, mock_add_error_record):
    mock_expr_checker = MagicMock()
    data_parser = MagicMock()
    data_parser.get_data_format.return_value = "fhir"
    data_parser.extract_field_values.side_effect = Exception("boom")

    self.validator._validate_expression(mock_expr_checker, self.expression, data_parser, [], True)

    mock_add_error_record.assert_called_once()
    args, _ = mock_add_error_record.call_args
    error_obj = args[1]
    self.assertIsInstance(error_obj, ErrorReport)
    self.assertEqual(error_obj.code, ExceptionLevels.PARSING_ERROR)


if __name__ == "__main__":
    unittest.main()
