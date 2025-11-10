from common.validator.error_report.dq_reporter import DQReporter
from src.common.validator.constants.enums import ErrorLevels
from src.common.validator.error_report.record_error import ErrorReport
from src.common.validator.parsers.paser_interface import PaserInterface


# Collect and add error record to the list
def add_error_record(
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
def check_error_record_for_fail(expression_identifier: str, error_records: list[ErrorReport]) -> bool:
    for error_record in error_records:
        if error_record.id == expression_identifier:
            return True
    return False


def build_error_report(event_id: str, data_parser: PaserInterface, error_records: list[ErrorReport]) -> dict:
    if data_parser.get_data_format() == "fhir":
        occurrence_date_time = data_parser.extract_field_value("occurrenceDateTime")
    else:
        occurrence_date_time = data_parser.extract_field_value("DATE_AND_TIME")

    dq_reporter = DQReporter()
    return dq_reporter.generate_error_report(event_id, occurrence_date_time, error_records)


def has_validation_failed(error_records: list[ErrorReport]) -> bool:
    return any(er.error_level == ErrorLevels.CRITICAL_ERROR for er in error_records)
