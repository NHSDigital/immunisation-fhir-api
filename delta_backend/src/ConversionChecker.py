
# Handles the transformation logic for each field based on the schema
# Root and base type expression checker functions
import ExceptionMessages
from datetime import datetime,timedelta, timezone
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
            case "DOSESEQUENCE":
                return self._convertToDose(
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
            case "BOOLEAN":
                return self._convertToBoolean(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "LOOKUP":
                return self._convertToLookUp(
                    expressionRule, fieldName, fieldValue, self.summarise, self.report_unexpected_exception
                )
            case "SNOMED":
                return self._convertToSnomed(
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
            case "JQ":
                return fieldValue
            case _:
                raise ValueError("Schema expression not found! Check your expression type : " + expressionType) 

    # Utility function for logging errors
    def _log_error(self, fieldName, fieldValue, e, code=ExceptionMessages.RECORD_CHECK_FAILED):
        if isinstance(e, Exception):
            message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, str(e))
        else:
            message = str(e)  # if a simple string message was passed 

        self.errorRecords.append({
            "code": code,
            "field": fieldName,
            "value": fieldValue,
            "message": message
        })

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
    

    # Not Empty Validate - Returns exactly what is in the extracted fields no parsing or logic needed
    def _convertToNotEmpty(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if isinstance(fieldValue, str) and fieldValue.strip():
                return fieldValue
            self._log_error(fieldName, fieldValue, "Value not a String")
            return ""
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(fieldName, fieldValue, message)
            return ""

    # NHSNumber Validate
    def _convertToNHSNumber(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        """
        Validates that the NHS Number is exactly 10 digits.
        """
        # If it is outright empty, return back an empty string
        if not fieldValue:
            return ""

        try:
            regexRule = r"^\d{10}$"
            if isinstance(fieldValue, str) and re.fullmatch(regexRule, fieldValue):
                return fieldValue
            raise ValueError(f"NHS Number must be exactly 10 digits: {fieldValue}")
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self.errorRecords.append({
                "field": fieldName,
                "value": fieldValue,
                "message": message
            })
        return ""

    # Gender Validate
    def _convertToGender(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
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
            normalized_gender = str(fieldValue).lower()

            if normalized_gender not in gender_map:
                return ""
            return gender_map[normalized_gender]

        except Exception as e:
            if report_unexpected_exception:
                return f"Unexpected exception [{e.__class__.__name__}]: {str(e)}"

    # Code for converting Action Flag
    def _convertToChangeTo(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            return expressionRule
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message
    # Code for converting Dose Sequence
    def _convertToDose(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        if isinstance(fieldValue, (int, float)) and 1 <= fieldValue <= 9:
            return fieldValue
        return "" 

    # Change to Lookup (loads expected data as is but if empty use lookup extraction to populate value)
    def _convertToLookUp(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        if isinstance(fieldValue, str) and any(char.isalpha() for char in fieldValue) and not fieldValue.isdigit():
            return fieldValue
        try:
                lookUpValue = self.dataParser.getKeyValue(expressionRule)
                IdentifiedLookup = self.dataLookUp.findLookUp(lookUpValue[0])
                return IdentifiedLookup

        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(fieldName, fieldValue, message)
            return ""

    # Default to Validate
    def _convertToDefaultTo(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if fieldValue == "":
                return expressionRule
            return str(fieldValue)
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

    # Check if Snomed code is numeric and reject other forms
    def _convertToSnomed(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        """
        Validates that a SNOMED code is a non-empty string containing only digits.
        """
        try:
            if not fieldValue:
                return fieldValue
            if not isinstance(fieldValue, str) or not fieldValue.isdigit():
                raise ValueError(f"Invalid SNOMED code: {fieldValue}")
            return fieldValue
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                self._log_error(fieldName, fieldValue, message)
            return ""

    # Check if Input is boolean or if input is a string with true or false, convert to Boolean
    def _convertToBoolean(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            if isinstance(fieldValue, bool):
                return fieldValue

            if str(fieldValue).strip().lower() == "true":
                return True
            if str(fieldValue).strip().lower() == "false":
                return False
            elif report_unexpected_exception:
                    self._log_error(fieldName, fieldValue, "Invalid String Data")
            return "" 
        except Exception as e:
            if report_unexpected_exception:
                 self._log_error(fieldName, fieldValue, e)
            return ""

    def get_error_records(self):
        return self.errorRecords