import datetime
import json

from dateutil import parser

from common.validator.enums.error_levels import ErrorLevels
from common.validator.record_error import ErrorReport


class DQReporter:
    def __init__(self):
        # parser variables
        self.error_report = {
            "eventId": "",
            "validationDate": "",
            "validated": "true",
            "results": {
                "totalErrors": 0,
                "completeness": {"errors": 0, "fields": []},
                "consistency": {"errors": 0, "fields": []},
                "validity": {"errors": 0, "fields": []},
                "timeliness_processed": 0,
            },
        }

    # create the date difference for the report in minutes
    def diff_dates(self, date1, date2):
        diff_seconds = abs(date2 - date1).total_seconds()
        diff_minutes = diff_seconds / 60
        return diff_minutes

    def generate_error_report(self, event_id, occurrence, error_records: list[ErrorReport]):
        occurrence_date = occurrence
        occurrence_date = parser.parse(occurrence_date, ignoretz=True)
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
