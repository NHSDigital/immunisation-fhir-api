import json
import datetime
import validator.enums.error_levels as ErrorLevels
from dateutil import parser

ErrorReport = {
    "eventId": "",
    "validationDate": "",
    "validated": 'true',
    "results": {
        "totalErrors": 0,
        "completeness": {
            "errors": 0,
            "fields": []
            },
        "consistency": {
            "errors": 0,
            "fields": []
            },
        "validity": {
            "errors": 0,
            "fields": []
            },
        "timeliness_processed": 0
        }
}


class DQReporter:

    # create the date difference for the report in minutes
    def diff_dates(self, date1, date2):
        diffSeconds = abs(date2-date1).total_seconds()
        diffMinutes = diffSeconds / 60
        return diffMinutes

    def generateErrorReport(self, eventId, Occurrence, error_records):
        occurenceDate = Occurrence
        occurenceDate = parser.parse(occurenceDate, ignoretz=True)
        validationDate = datetime.datetime.now(tz=None)

        timeTaken = self.diff_dates(occurenceDate, validationDate)

        ErrorReport['validationDate'] = validationDate.isoformat()
        ErrorReport['eventId'] = eventId
        ErrorReport['results']['timeliness_processed'] = timeTaken

        for errorRecord in error_records:
            self.updateReport(errorRecord)

        jsonErrorReport = json.dumps(ErrorReport)
        return jsonErrorReport

    def updateReport(self, errorData):
        errorGroup = errorData["errorGroup"]
        if (errorData['errorLevel'] == ErrorLevels.CRITICAL_ERROR):
            ErrorReport['validated'] = "false"
        totalErrors = ErrorReport['results']['totalErrors']
        resultsErrorCount = ErrorReport['results'][errorGroup]['errors']
        resultsErrorCount += 1
        totalErrors += 1
        ErrorReport['results'][errorGroup]['fields'].append(errorData["name"])
        ErrorReport['results'][errorGroup]['errors'] = resultsErrorCount
        ErrorReport['results']['totalErrors'] = totalErrors
