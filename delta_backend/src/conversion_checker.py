
# Handles the transformation logic for each field based on the schema
# Root and base type expression checker functions
import exception_messages
from datetime import datetime,timedelta, timezone
import re

# --------------------------------------------------------------------------------------------------------
# Custom error type to handle validation failures
class RecordError(Exception):

    def __init__(self, code=None, message=None, details=None):
        self.code = code
        self.message = message
        self.details = details

    def __str__(self):
        return repr((self.code, self.message, self.details))

    def __repr__(self):
        return repr((self.code, self.message, self.details))


# ---------------------------------------------------------------------------------------------------------
# main conversion checker
# Conversion engine for expression-based field transformation
class ConversionChecker:
    # checker settings
    summarise = False
    report_unexpected_exception = True
    dataParser = any

    def __init__(self, dataParser, summarise, report_unexpected_exception):
        self.dataParser = dataParser  # FHIR data parser for additional functions
        self.summarise = summarise  # instance attribute
        self.report_unexpected_exception = report_unexpected_exception  # instance attribute
        self.errorRecords = []  # Store all errors here

    # Main entry point called by converter.py
    def convertData(self, expressionType, expressionRule, fieldName, fieldValue):
        match expressionType:
            case "DATECONVERT":
                return self._convertToDate(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "DATETIME":
                return self._convertToDateTime(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "DEFAULT":
                # TODO - check expression_rule is callable
                return expressionRule()
            case _:
                raise ValueError("Schema expression not found! Check your expression type : " + expressionType)

    def _convertToDate(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
            """
            Convert a date string according to match YYYYMMDD format.
            """
            if not fieldValue:
                return ""

            # 1. Data type must be a string
            if not isinstance(fieldValue, str):
                if report_unexpected_exception:
                    self._log_error(fieldName, fieldValue, "Value is not a string")
                return ""
            try:
                dt = datetime.fromisoformat(fieldValue)
                return dt.strftime(expressionRule)
            except ValueError as e:
                # 5. Unexpected parsing errors
                if report_unexpected_exception:
                    self._log_error(fieldName, fieldValue, e)
                return ""

    # Convert FHIR datetime into CSV-safe UTC format
    def _convertToDateTime(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        if not fieldValue:
            return ""

        try:
            dt = datetime.fromisoformat(fieldValue)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            if report_unexpected_exception:
                self._log_error(fieldName, fieldValue, e)
            return ""

        # Allow only +00:00 or +01:00 offsets (UTC and BST) and reject unsupported timezones
        offset = dt.utcoffset()
        allowed_offsets = [timedelta(hours=0), timedelta(hours=1)]
        if offset is not None and offset not in allowed_offsets:
            if report_unexpected_exception:
                self._log_error(fieldName, fieldValue, "Unsupported Format or offset")
            return ""

        # remove microseconds
        dt_format = dt.replace(microsecond=0)

        formatted = dt_format.strftime("%Y%m%dT%H%M%S%z")
        return formatted.replace("+0000", "00").replace("+0100", "01")

     # Utility function for logging errors
    def _log_error(self, fieldName, fieldValue, e, code=exception_messages.RECORD_CHECK_FAILED):
        if isinstance(e, Exception):
            message = exception_messages.MESSAGES[exception_messages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, str(e))
        else:
            message = str(e)  # if a simple string message was passed

        self.errorRecords.append({
            "code": code,
            "field": fieldName,
            "value": fieldValue,
            "message": message
        })
        
    def get_error_records(self):
        return self.errorRecords
