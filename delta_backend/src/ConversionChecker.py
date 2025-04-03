
# Handles the transformation logic for each field based on the schema
# Root and base type expression checker functions
import ExceptionMessages
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import re
from LookUpData import LookUpData


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
    dataLookUp = any

    def __init__(self, dataParser, summarise, report_unexpected_exception):
        self.dataParser = dataParser  # FHIR data parser for additional functions
        self.dataLookUp = LookUpData()  # used for generic look up
        self.summarise = summarise  # instance attribute
        self.report_unexpected_exception = report_unexpected_exception  # instance attribute

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
            case "NOTEMPTY":
                return self._convertToNotEmpty(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "GENDER":
                return self._convertToGender(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "NHSNUMBER":
                return self._convertToNHSNumber(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "CHANGETO":
                return self._convertToChangeTo(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "LOOKUP":
                return self._convertToLookUp(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "DEFAULT":
                return self._convertToDefaultTo(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "ONLYIF":
                return self._convertToOnlyIfTo(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case _:
                return "Schema expression not found! Check your expression type : " + expressionType

    # Convert ISO date string to a specific format (e.g. YYYYMMDD)
    def _convertToDate(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        if not fieldValue:
            return ""

        if not isinstance(fieldValue, str):
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{fieldName} rejected: not a string.",
                f"Received: {type(fieldValue)}",
        )
        # Reject partial dates like "2024" or "2024-05"
        if re.match(r"^\d{4}(-\d{2})?$", fieldValue):
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{fieldName} rejected: partial date not accepted.",
                f"Invalid partial date: {fieldValue}",
            )
        try:
            dt = datetime.fromisoformat(fieldValue)
            format_str = expressionRule.replace("format:", "")
            return dt.strftime(format_str)
        except ValueError:
            if report_unexpected_exception:
                return f"Unexpected format: {fieldValue}"

    # Convert FHIR datetime into CSV-safe UTC format
    def _convertToDateTime(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        if not fieldValue:
            return ""

        # Reject partial dates like "2024" or "2024-05"
        if re.match(r"^\d{4}(-\d{2})?$", fieldValue):
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{fieldName} rejected: partial datetime not accepted.",
                f"Invalid partial datetime: {fieldValue}",
            )
        try:
            dt = datetime.fromisoformat(fieldValue)
        except ValueError:
            if report_unexpected_exception:
                return f"Unexpected format: {fieldValue}"

        # Allow only +00:00 or +01:00 offsets (UTC and BST) and reject unsupported timezones
        offset = dt.utcoffset()
        allowed_offsets = [ZoneInfo("UTC").utcoffset(dt),
                           ZoneInfo("Europe/London").utcoffset(dt)]
        if offset not in allowed_offsets:
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{fieldName} rejected: unsupported timezone.",
                f"Unsupported offset: {offset}",
            )

        # Convert to UTC
        dt_utc = dt.astimezone(ZoneInfo("UTC")).replace(microsecond=0)

        format_str = expressionRule.replace("format:", "")

        if format_str == "csv-utc":
            formatted = dt_utc.strftime("%Y%m%dT%H%M%S%z")
            return formatted.replace("+0000", "00").replace("+0100", "01")

        return dt_utc.strftime(format_str)

    # Not Empty Validate
    def _convertToNotEmpty(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if len(str(fieldValue)) > 0:
                return fieldValue
            return ""
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # NHSNumber Validate
    def _convertToNHSNumber(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            regexRule = "^6[0-9]{10}$"
            result = re.search(regexRule, fieldValue)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "NHS Number check failed",
                    "NHS Number does not meet regex rules, data- " + fieldValue,
                )
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Gender Validate
    def _convertToGender(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            genderlist = {"male": "1", "female": "2", "other": "9", "unknown": "0"}
            genderNumber = genderlist[fieldValue]
            return genderNumber
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Change to Validate
    def _convertToChangeTo(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            return expressionRule
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Change to Lookup
    def _convertToLookUp(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if fieldValue != "":
                return fieldValue
            try:
                lookUpValue = self.dataParser.getKeyValue(expressionRule)
                IdentifiedLookup = self.dataLookUp.findLookUp(lookUpValue[0])
                return IdentifiedLookup
            except:
                return ""
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Default to Validate
    def _convertToDefaultTo(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if fieldValue == "":
                return expressionRule
            return fieldValue
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Default to Validate
    def _convertToOnlyIfTo(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            conversionList = expressionRule.split("|")
            location = conversionList[0]
            valueCheck = conversionList[1]
            dataValue = self.dataParser.getKeyValue(location)

            if dataValue[0] != valueCheck:
                return ""

            return fieldValue
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message
