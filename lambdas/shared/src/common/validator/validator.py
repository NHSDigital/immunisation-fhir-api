# Main validation engine

from enum import Enum

import common.validator.enums.error_levels as ErrorLevels
import common.validator.enums.exception_messages as ExceptionMessages
from common.validator.expression_checker import ExpressionChecker
from common.validator.parsers.csv_line_parser import CSVLineParser
from common.validator.parsers.csv_parser import CSVParser
from common.validator.parsers.fhir_parser import FHIRParser
from common.validator.parsers.schema_parser import SchemaParser
from common.validator.record_error import ErrorReport
from common.validator.reporter.dq_reporter import DQReporter


class DataType(Enum):
    FHIR = "FHIR"
    FHIRJSON = "FHIRJSON"
    CSV = "CSV"
    CSVROW = "CSVROW"


class Validator:
    def __init__(self, schema_file="", data_type: DataType = None, filepath=""):
        self.filepath = filepath
        self.json_data = {}
        self.schema_file = schema_file
        self.csv_row = ""
        self.csv_header = ""
        self.data_type = data_type
        self.data_parser = ""
        self.error_records: list[ErrorReport] = []

    def _get_csv_line_parser(self, csv_row, csv_header):
        csv_parser = CSVLineParser()
        csv_parser.parse_csv_line(csv_row, csv_header)
        return csv_parser

    def _get_csv_parser(self, filepath):
        csv_parser = CSVParser()
        csv_parser.parse_csv_file(filepath)
        return csv_parser

    def _get_fhir_parser(self, filepath):
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_file(filepath)
        return fhir_parser

    def _get_fhir_json_parser(self, fhir_data):
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_data(fhir_data)
        return fhir_parser

    def _get_schema_parser(self, schemafile):
        schema_parser = SchemaParser()
        schema_parser.parse_schema(schemafile)
        return schema_parser

    def _add_error_record(
        self, error_record: ErrorReport, expression_error_group, expression_name, expression_id, error_level
    ):
        if error_record is not None:
            error_record.error_group = expression_error_group
            error_record.name = expression_name
            error_record.id = expression_id
            error_record.error_level = error_level
            self.error_records.append(error_record)

    # Function to help identify a parent failure in the error list
    def _check_error_record_for_fail(self, expression_id):
        for error_record in self.error_records:
            if error_record.id == expression_id:
                return True
        return False

    #  validate a single expression against the data file
    def _validate_expression(
        self, expression_validator: ExpressionChecker, expression, inc_header_in_row_count
    ) -> ErrorReport | int:
        row = 1
        if inc_header_in_row_count:
            row = 2

        if self.isCSV:
            expression_fieldname = expression["fieldNameCSV"]
        else:
            expression_fieldname = expression["fieldNameFHIR"]

        expression_id = expression["expressionId"]
        error_level = expression["errorLevel"]
        expression_name = expression["expression"]["expressionName"]
        expression_type = expression["expression"]["expressionType"]
        expression_rule = expression["expression"]["expressionRule"]
        expression_error_group = expression["errorGroup"]

        # Check to see if the expression has a parent, if so did the parent validate
        if "parentExpression" in expression:
            parent_expression = expression["parentExpression"]
            if self._check_error_record_for_fail(parent_expression):
                error_record = {
                    "code": ExceptionMessages.PARENT_FAILED,
                    "message": ExceptionMessages.MESSAGES[ExceptionMessages.PARENT_FAILED]
                    + ", Parent ID: "
                    + parent_expression,
                }
                self._add_error_record(
                    error_record, expression_error_group, expression_name, expression_id, error_level
                )
                return error_record

        try:
            expression_values = self.data_parser.get_key_value(expression_fieldname)
        except Exception as e:
            message = f"Data get values Unexpected exception [{e.__class__.__name__}]: {e}"
            error_report = ErrorReport(code=ExceptionMessages.PARSING_ERROR, message=message)
            # original code had self.CriticalErrorLevel. Replaced with error_level
            self._add_error_record(error_report, expression_error_group, expression_name, expression_id, error_level)
            return error_report

        for value in expression_values:
            error_record: ErrorReport | None = None
            try:
                error_record = expression_validator.validate_expression(
                    expression_type, expression_rule, expression_fieldname, value, row
                )
                if error_record is not None:
                    self._add_error_record(
                        error_record, expression_error_group, expression_name, expression_id, error_level
                    )
            except Exception:
                print(f"Exception validating expression {expression_id} on row {row}: {error_record}")
            row += 1
        return row

    def validate_fhir(
        self, filepath, summarise=False, report_unexpected_exception=True, inc_header_in_row_count=True
    ) -> list[ErrorReport]:
        self.data_type = DataType.FHIR
        self.filepath = filepath
        return self.run_validation(summarise, report_unexpected_exception, inc_header_in_row_count)

    def validate_csv(
        self, filepath, summarise=False, report_unexpected_exception=True, inc_header_in_row_count=True
    ) -> list[ErrorReport]:
        self.data_type = DataType.CSV
        self.filepath = filepath
        return self.run_validation(summarise, report_unexpected_exception, inc_header_in_row_count)

    def validate_csv_row(
        self, csv_row, csv_header, summarise=False, report_unexpected_exception=True, inc_header_in_row_count=True
    ) -> list[ErrorReport]:
        self.data_type = DataType.CSVROW
        self.csv_row = csv_row
        self.csv_header = csv_header
        return self.run_validation(summarise, report_unexpected_exception, inc_header_in_row_count)

    def validate_fhir_json(
        self, json_data, summarise=False, report_unexpected_exception=True, inc_header_in_row_count=True
    ) -> list[ErrorReport]:
        self.data_type = DataType.FHIRJSON
        self.json_data = json_data
        return self.validate_fhir_json(json_data, summarise, report_unexpected_exception, inc_header_in_row_count)

    # run the validation against the data
    def run_validation(
        self, summarise=False, report_unexpected_exception=True, inc_header_in_row_count=True
    ) -> list[ErrorReport]:
        try:
            self.error_records.clear()

            match self.data_type:  # 'FHIR', 'FHIRJSON', 'CSV', 'CSVROW'
                case DataType.FHIR:
                    self.data_parser = self._get_fhir_parser(self.filepath)
                    self.isCSV = False
                case DataType.FHIRJSON:
                    self.data_parser = self._get_fhir_json_parser(self.json_data)
                    self.isCSV = False
                case DataType.CSV:
                    self.data_parser = self._get_csv_parser(self.filepath)
                    self.isCSV = True
                case DataType.CSVROW:
                    self.data_parser = self._get_csv_line_parser(self.csv_row, self.csv_header)
                    self.isCSV = True

        except Exception as e:
            if report_unexpected_exception:
                message = f"Data Parser Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        try:
            schemaParser = self._get_schema_parser(self.schema_file)
        except Exception as e:
            if report_unexpected_exception:
                message = f"Schema Parser Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        try:
            expression_validator = ExpressionChecker(self.data_parser, summarise, report_unexpected_exception)
        except Exception as e:
            if report_unexpected_exception:
                message = f"Expression Checker Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        # get list of expressions
        try:
            expressions = schemaParser.get_expressions()
        except Exception as e:
            if report_unexpected_exception:
                message = f"Expression Getter Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        for expression in expressions:
            self._validate_expression(expression_validator, expression, inc_header_in_row_count)

        return self.error_records

    # -------------------------------------------------------------------------
    # Report Generation
    # Build the error Report
    def build_error_report(self, eventId):
        OccurrenceDateTime = self.data_parser.get_key_single_value("occurrenceDateTime")
        dq_reporter = DQReporter()
        dq_report = dq_reporter.generate_error_report(eventId, OccurrenceDateTime, self.error_records)

        return dq_report

    # Check all errors to see if we have a critical error that would fail the validation
    def has_validation_failed(self):
        for error_record in self.error_records:
            if error_record.error_level == ErrorLevels.CRITICAL_ERROR:
                return True
        return False
