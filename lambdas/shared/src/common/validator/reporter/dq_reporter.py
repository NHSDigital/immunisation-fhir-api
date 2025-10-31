import datetime
import json

from dateutil import parser

from common.validator.constants.enums import ErrorLevels
from common.validator.constants.error_report import error_report
from common.validator.record_error import ErrorReport


class DQReporter:
    """
    Generates error reports based on validation results.
    It uses cumulates all error records, assigns them to the appropriate error levels,
    checks the time difference between event occurrence and validation time,
    and builds a structured error report in JSON format.
    """

    def __init__(self):
        # parser variables
        self.error_report = error_report

    # create the date difference for the report in minutes
    def diff_dates(self, fhir_event_date, current_date):
        diff_seconds = abs(current_date - fhir_event_date).total_seconds()
        diff_minutes = diff_seconds / 60
        return diff_minutes

    def generate_error_report(self, event_id, occurrence_date_time, error_records: list[ErrorReport]):
        occurrence_date = parser.parse(occurrence_date_time, ignoretz=True)
        validation_date = datetime.datetime.now(tz=None)

        time_taken = self.diff_dates(occurrence_date, validation_date)

        self.error_report["validationDate"] = validation_date.isoformat()
        self.error_report["eventId"] = event_id
        self.error_report["results"]["timeliness_processed"] = time_taken

        for error_record in error_records:
            self.update_report(error_record)

        json_error_report = json.dumps(self.error_report)
        return json_error_report

    def update_report(self, error_data: ErrorReport):
        error_group = error_data.error_group
        if error_data.error_level == ErrorLevels.CRITICAL_ERROR:
            self.error_report["validated"] = "false"
        total_errors = self.error_report["results"]["totalErrors"]
        results_error_count = self.error_report["results"][error_group]["errors"]
        results_error_count += 1
        total_errors += 1
        self.error_report["results"][error_group]["fields"].append(error_data.name)
        self.error_report["results"][error_group]["errors"] = results_error_count
        self.error_report["results"]["totalErrors"] = total_errors
