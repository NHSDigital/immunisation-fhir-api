
# Handles the transformation logic for each field based on the schema
# Root and base type expression checker functions
import ExceptionMessages
from datetime import datetime,timezone
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
        self.errorRecords = []  # Store all errors here

    # Main entry point called by converter.py
    def convertData(self, expressionType,expression_rule, field_name, field_value):
        match expressionType:
            case "DATECONVERT":
                return self._convertToDate(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "DATETIME":
                return self._convertToDateTime(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "NOTEMPTY":
                return self._convertToNotEmpty(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "DOSESEQUENCE":
                return self._convertToDose(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "GENDER":
                return self._convertToGender(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "NHSNUMBER":
                return self._convertToNHSNumber(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "CHANGETO":
                return self._convertToChangeTo(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "BOOLEAN":
                return self._convertToBoolean(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "LOOKUP":
                return self._convertToLookUp(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "DEFAULT":
                return self._convertToDefaultTo(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case "ONLYIF":
                return self._convertToOnlyIfTo(
                   expression_rule, field_name, field_value, self.summarise, self.report_unexpected_exception
                )
            case _:
                raise ValueError("Schema expression not found! Check your expression type : " + expressionType) 

    # Utility function for logging errors
    def _log_error(self, field_name, field_value, e, code=ExceptionMessages.RECORD_CHECK_FAILED):
        if isinstance(e, Exception):
            message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, str(e))
        else:
            message = str(e)  # if a simple string message was passed 

        self.errorRecords.append({
            "code": code,
            "field": field_name,
            "value": field_value,
            "message": message
        })

    def _convertToDate(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
            """
            Convert a date string according to match YYYYMMDD format. 
            """
            if not field_value:
                return ""

            # 1. Data type must be a string
            if not isinstance(field_value, str):
                if report_unexpected_exception:
                    self._log_error(field_name, field_value, "Value is not a string")
                return ""

            # 2. Use Expression Rule Format to parse the date, remove dashes and slashes
            if expression_rule == "%Y%m%d":
                field_value = field_value.split("T")[0]
                field_value = field_value.replace("-", "").replace("/", "")
                if not re.match(r"^\d{8}$", field_value):
                    if report_unexpected_exception:
                        self._log_error(field_name, field_value, "Date must be in YYYYMMDD format")
                    return ""
            try:
                # Converts raw fieldvalue without delimiters to a date-time object
                dt = datetime.strptime(field_value,expression_rule)
                return dt.strftime(expression_rule)
            except ValueError as e:
                # 5. Unexpected parsing errors
                if report_unexpected_exception:
                    self._log_error(field_name, field_value, e)
                return ""

    # Convert FHIR datetime into CSV-safe UTC format
    def _convertToDateTime(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        if not field_value:
            return ""

        # Reject partial dates like "2024" or "2024-05"
        if re.match(r"^\d{4}(-\d{2})?$", field_value):
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{field_name} rejected: partial datetime not accepted.",
                f"Invalid partial datetime: {field_value}",
            )
        try:
            dt = datetime.fromisoformat(field_value)
        except ValueError:
            if report_unexpected_exception:
                return f"Unexpected format: {field_value}"

        # Allow only +00:00 or +01:00 offsets (UTC and BST) and reject unsupported timezones
        offset = dt.utcoffset()
        allowed_offsets = [ZoneInfo("UTC").utcoffset(dt),
                           ZoneInfo("Europe/London").utcoffset(dt)]
        if offset not in allowed_offsets:
            raise RecordError(
                ExceptionMessages.RECORD_CHECK_FAILED,
                f"{field_name} rejected: unsupported timezone.",
                f"Unsupported offset: {offset}",
            )

        # Convert to UTC
        dt_utc = dt.astimezone(ZoneInfo("UTC")).replace(microsecond=0)

        format_str =expression_rule.replace("format:", "")

        if format_str == "csv-utc":
            formatted = dt_utc.strftime("%Y%m%dT%H%M%S%z")
            return formatted.replace("+0000", "00").replace("+0100", "01")

        return dt_utc.strftime(format_str)

    # Not Empty Validate - Returns exactly what is in the extracted fields no parsing or logic needed
    def _convertToNotEmpty(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        try:
            if isinstance(field_value, str) and field_value.strip():
                return field_value
            self._log_error(field_name, field_value, "Value not a String")
            return ""
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(field_name, field_value, message)
            return

    # NHSNumber Validate
    def _convertToNHSNumber(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        """
        Validates that the NHS Number is exactly 10 digits.
        """
        # If it is outright empty, return back an empty string
        if not field_value:
            return ""

        try:
            regexRule = r"^\d{10}$"
            if isinstance(field_value, str) and re.fullmatch(regexRule, field_value):
                return field_value
            raise ValueError(f"NHS Number must be exactly 10 digits: {field_value}")
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self.errorRecords.append({
                "field": field_name,
                "value": field_value,
                "message": message
            })
        return ""

    # Gender Validate
    def _convertToGender(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        """
        Converts gender string to numeric representation.
        Mapping:
            - "male" → "1"
            - "female" → "2"
            - "other" → "9"
            - "unknown" → "0"
        """
        try:
            gender_map = {
                "male": "1",
                "female": "2",
                "other": "9",
                "unknown": "0"
            }

            # Normalize input
            normalized_gender = str(field_value).lower()

            if normalized_gender not in gender_map:
                return ""
            return gender_map[normalized_gender]

        except Exception as e:
            if report_unexpected_exception:
                return f"Unexpected exception [{e.__class__.__name__}]: {str(e)}"

    # Code for converting Action Flag
    def _convertToChangeTo(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        try:
            return expression_rule
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message
    # Code for converting Dose Sequence
    def _convertToDose(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        if isinstance(field_value, (int, float)) and 1 <= field_value <= 9:
            return field_value
        return "" 

    # Change to Lookup (loads expected data as is but if empty use lookup extraction to populate value)
    def _convertToLookUp(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        if isinstance(field_value, str) and any(char.isalpha() for char in field_value) and not field_value.isdigit():
            return field_value
        try:
                lookUpValue = self.dataParser.getKeyValue(expression_rule)
                IdentifiedLookup = self.dataLookUp.findLookUp(lookUpValue[0])
                return IdentifiedLookup

        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(field_name, field_value, message)
            return ""

    # Default to Validate
    def _convertToDefaultTo(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        try:
            if field_value == "":
                return expression_rule
            return field_value
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Default to Validate
    def _convertToOnlyIfTo(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        try:
            conversionList =expression_rule.split("|")
            location = conversionList[0]
            valueCheck = conversionList[1]
            dataValue = self.dataParser.getKeyValue(location)

            if dataValue[0] != valueCheck:
                return ""

            return field_value
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

    # Check if Snomed code is numeric and reject other forms
    def _convertToSnomed(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        """
        Validates that a SNOMED code is a non-empty string containing only digits.
        """
        try:
            if not field_value:
                return field_value
            if not isinstance(field_value, str) or not field_value.isdigit():
                raise ValueError(f"Invalid SNOMED code: {field_value}")
            return field_value
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(field_name, field_value, message)
            return ""

    # Check if Input is boolean or if input is a string with true or false, convert to Boolean
    def _convertToBoolean(self,expression_rule, field_name, field_value, summarise, report_unexpected_exception):
        try:
            if isinstance(field_value, bool):
                return field_value

            if str(field_value).strip().lower() == "true":
                return True
            if str(field_value).strip().lower() == "false":
                return False
            elif report_unexpected_exception:
                    self._log_error(field_name, field_value, "Invalid String Data")
            return "" 
        except Exception as e:
            if report_unexpected_exception:
                 self._log_error(field_name, field_value, e)
            return ""

    def get_error_records(self):
        return self.errorRecords