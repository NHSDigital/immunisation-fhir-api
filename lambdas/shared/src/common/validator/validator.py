"""
1. Runs the CSV and FHIR Parsers (where Extraction of the values occurs and collates extraction error reports)
2. Runs the Expresssion Checker against each expression in the schema
3. Collects all error records and builds the final error report
"""

from common.validator.constants.enums import MESSAGES, DataType, ErrorLevels, ExceptionLevels
from common.validator.expression_checker import ExpressionChecker
from common.validator.parsers.csv_line_parser import CSVLineParser
from common.validator.parsers.csv_parser import CSVParser
from common.validator.parsers.fhir_parser import FHIRParser
from common.validator.parsers.schema_parser import SchemaParser
from common.validator.record_error import ErrorReport
from common.validator.reporter.dq_reporter import DQReporter


class Validator:
    def __init__(self, schema_file=""):
        self.schema_file = schema_file

    # Retrieve all the Parsers,
    def _get_csv_parser(self, filepath: str) -> CSVParser:
        csv_parser = CSVParser()
        csv_parser.parse_csv_file(filepath)
        return csv_parser

    def _get_csv_line_parser(self, csv_row, csv_header) -> CSVLineParser:
        csv_line_parser = CSVLineParser()
        csv_line_parser.parse_csv_line(csv_row, csv_header)
        return csv_line_parser

    def _get_fhir_parser(self, fhir_data: dict) -> FHIRParser:
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_data(fhir_data)
        return fhir_parser

    def _get_schema_parser(self, schemafile: str) -> SchemaParser:
        schema_parser = SchemaParser()
        schema_parser.parse_schema(schemafile)
        return schema_parser

    # Collect and add error record to the list
    def _add_error_record(
        self,
        error_records: list[ErrorReport],
        error_record: ErrorReport,
        expression_error_group: str,
        expression_name: str,
        expression_id: str,
        error_level: ErrorLevels,
    ) -> None:
        if error_record is not None:
            error_record.error_group = expression_error_group
            error_record.name = expression_name
            error_record.id = expression_id
            error_record.error_level = error_level
            error_records.append(error_record)

    # Function to help identify a parent failure in the error list
    def _check_error_record_for_fail(self, expression_identifier: str, error_records: list[ErrorReport]) -> bool:
        for error_record in error_records:
            if error_record.id == expression_identifier:
                return True
        return False

    #  validate a single expression against the data file
    def _validate_expression(
        self,
        expression_validator: ExpressionChecker,
        expression: dict,
        data_parser,
        error_records: list[ErrorReport],
        inc_header_in_row_count: bool,
        is_csv: bool,
    ) -> ErrorReport | int:
        row = 2 if inc_header_in_row_count else 1
        expression_fieldname = expression["fieldNameFlat"] if is_csv else expression["fieldNameFHIR"]

        expression_id = expression["expressionId"]
        error_level = expression["errorLevel"]
        expression_name = expression["expression"]["expressionName"]
        expression_type = expression["expression"]["expressionType"]
        expression_rule = expression["expression"]["expressionRule"]
        expression_error_group = expression["errorGroup"]

        # Check to see if the expression has a parent, if so did the parent validate
        if "parentExpression" in expression:
            parent_expression = expression["parentExpression"]
            if self._check_error_record_for_fail(parent_expression, error_records):
                error_record = ErrorReport(
                    code=ExceptionLevels.PARENT_FAILED,
                    message=MESSAGES[ExceptionLevels.PARENT_FAILED] + ", Parent ID: " + parent_expression,
                )
                self._add_error_record(
                    error_records, error_record, expression_error_group, expression_name, expression_id, error_level
                )
                return

        try:
            expression_values = data_parser.get_key_value(expression_fieldname)
        except Exception as e:
            message = f"Data get values Unexpected exception [{e.__class__.__name__}]: {e}"
            error_record = ErrorReport(code=ExceptionLevels.PARSING_ERROR, message=message)
            # original code had self.CriticalErrorLevel. Replaced with error_level
            self._add_error_record(
                error_records, error_record, expression_error_group, expression_name, expression_id, error_level
            )
            return

        for value in expression_values:
            try:
                error_record = expression_validator.validate_expression(
                    expression_type, expression_rule, expression_fieldname, value, row
                )
                if error_record is not None:
                    self._add_error_record(
                        error_records, error_record, expression_error_group, expression_name, expression_id, error_level
                    )
            except Exception:
                print(f"Exception validating expression {expression_id} on row {row}: {error_record}")
            row += 1
        return row

    def validate_fhir(
        self,
        fhir_data: dict,
        summarise: bool = False,
        report_unexpected_exception: bool = True,
        inc_header_in_row_count: bool = True,
    ) -> list[ErrorReport]:
        return self.run_validation(
            data_type=DataType.FHIR,
            fhir_data=fhir_data,
            summarise=summarise,
            report_unexpected_exception=report_unexpected_exception,
            inc_header_in_row_count=inc_header_in_row_count,
        )

    def validate_csv(
        self,
        batch_filepath: str,
        summarise: bool = False,
        report_unexpected_exception: bool = True,
        inc_header_in_row_count: bool = True,
    ) -> list[ErrorReport]:
        return self.run_validation(
            data_type=DataType.CSV,
            batch_filepath=batch_filepath,
            summarise=summarise,
            report_unexpected_exception=report_unexpected_exception,
            inc_header_in_row_count=inc_header_in_row_count,
        )

    def validate_csv_row(
        self,
        csv_row: str,
        csv_header: list[str],
        summarise: bool = False,
        report_unexpected_exception: bool = True,
        inc_header_in_row_count: bool = True,
    ) -> list[ErrorReport]:
        return self.run_validation(
            data_type=DataType.CSVROW,
            csv_row=csv_row,
            csv_header=csv_header,
            summarise=summarise,
            report_unexpected_exception=report_unexpected_exception,
            inc_header_in_row_count=inc_header_in_row_count,
        )

    # run the validation against the data
    def run_validation(
        self,
        data_type: DataType,
        fhir_data: dict = None,
        batch_filepath: str = None,
        csv_row: str = None,
        csv_header: list[str] = None,
        summarise=False,
        report_unexpected_exception=True,
        inc_header_in_row_count=True,
    ) -> list[ErrorReport]:
        error_records: list[ErrorReport] = []

        try:
            match data_type:
                case DataType.FHIR:
                    data_parser = self._get_fhir_parser(fhir_data)
                    is_csv = False
                case DataType.CSV:
                    data_parser = self._get_csv_parser(batch_filepath)
                    is_csv = True
                case DataType.CSVROW:
                    data_parser = self._get_csv_line_parser(csv_row, csv_header)
                    is_csv = True

        except Exception as e:
            if report_unexpected_exception:
                message = f"Data Parser Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        schema_parser = self._get_schema_parser(self.schema_file)
        expression_validator = ExpressionChecker(data_parser, summarise, report_unexpected_exception)
        expressions = schema_parser.get_expressions()

        for expression in expressions:
            self._validate_expression(
                expression_validator, expression, data_parser, error_records, inc_header_in_row_count, is_csv
            )

        return error_records

    # Build the error Report
    def build_error_report(self, event_id: str, data_parser, error_records: list[ErrorReport]) -> dict:
        occurrence_date_time = data_parser.get_fhir_value("occurrenceDateTime")
        dq_reporter = DQReporter()
        return dq_reporter.generate_error_report(event_id, occurrence_date_time, error_records)

    def has_validation_failed(self, error_records: list[ErrorReport]) -> bool:
        return any(er.error_level == ErrorLevels.CRITICAL_ERROR for er in error_records)
