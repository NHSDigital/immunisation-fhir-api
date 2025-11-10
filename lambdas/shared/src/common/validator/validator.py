"""
1. Runs the CSV and FHIR Parsers (where Extraction of the values occurs and collates extraction error reports)
2. Runs the Expresssion Checker against each expression in the schema
3. Collects all error records and builds the final error report
data_parser is the date parser object returned from the FetchParsers class which contains the data to be validated either fhir or csv
"""

from common.validator.constants.enums import MESSAGES, DataType, ErrorLevels, ExceptionLevels
from common.validator.error_report.error_reporter import add_error_record, check_error_record_for_fail
from common.validator.error_report.record_error import ErrorReport
from common.validator.expression_checker import ExpressionChecker
from common.validator.parsers.schema_parser import SchemaParser
from src.common.validator.parsers.paser_interface import BatchInterface, FHIRInterface, PaserInterface


class Validator:
    def __init__(self, schema_file=""):
        self.schema_file = schema_file
        self.schema_parser = SchemaParser()

    #  validate expression against incoming data
    def _validate_expression(
        self,
        expression_validator: ExpressionChecker,
        expression: dict,
        data_parser: PaserInterface,
        error_records: list[ErrorReport],
        inc_header_in_row_count: bool,
    ) -> ErrorReport | int:
        row = 2 if inc_header_in_row_count else 1

        data_format = data_parser.get_data_format()
        expression_fieldname = expression["fieldNameFlat"] if data_format == "batch" else expression["fieldNameFHIR"]

        expression_id = expression["expressionId"]
        error_level = expression["errorLevel"]
        expression_name = expression["expression"]["expressionName"]
        expression_type = expression["expression"]["expressionType"]
        expression_rule = expression["expression"]["expressionRule"]
        expression_error_group = expression["errorGroup"]

        # Check to see if the expression has a parent, if so did the parent validate
        if "parentExpression" in expression:
            parent_expression = expression["parentExpression"]
            if check_error_record_for_fail(parent_expression, error_records):
                error_record = ErrorReport(
                    code=ExceptionLevels.PARENT_FAILED,
                    message=MESSAGES[ExceptionLevels.PARENT_FAILED] + ", Parent ID: " + parent_expression,
                )
                add_error_record(
                    error_records, error_record, expression_error_group, expression_name, expression_id, error_level
                )
                return

        try:
            expression_values = data_parser.extract_field_values(expression_fieldname)
            print(f"Extracted values for field {expression_fieldname}: {expression_values}")
        except Exception as e:
            message = f"Data get values Unexpected exception [{e.__class__.__name__}]: {e}"
            error_record = ErrorReport(code=ExceptionLevels.PARSING_ERROR, message=message)
            # original code had self.CriticalErrorLevel. Replaced with error_level
            add_error_record(
                error_records, error_record, expression_error_group, expression_name, expression_id, error_level
            )
            return

        for value in expression_values:
            try:
                error_record = expression_validator.validate_expression(
                    expression_type, expression_rule, expression_fieldname, value, row
                )
                if error_record is not None:
                    add_error_record(
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
                    data_parser = FHIRInterface(fhir_data)
                case DataType.CSVROW:
                    data_parser = BatchInterface(csv_row, csv_header)

        except Exception as e:
            if report_unexpected_exception:
                message = f"Data Parser Unexpected exception [{e.__class__.__name__}]: {e}"
                return [ErrorReport(code=0, message=message)]

        schema_parser = self.schema_parser.parse_schema(self.schema_file)
        expression_validator = ExpressionChecker(data_parser, summarise, report_unexpected_exception)
        expressions_in_schema = schema_parser.get_expressions()

        for expression in expressions_in_schema:
            self._validate_expression(
                expression_validator, expression, data_parser, error_records, inc_header_in_row_count
            )

        return error_records

    def has_validation_failed(self, error_records: list[ErrorReport]) -> bool:
        return any(er.error_level == ErrorLevels.CRITICAL_ERROR for er in error_records)
