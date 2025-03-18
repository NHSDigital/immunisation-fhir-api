# Root and base type expression checker functions
import ExceptionMessages
import datetime
import uuid
import re
from LookUpData import LookUpData


# --------------------------------------------------------------------------------------------------------
# record exception capture
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

    # exposed functions
    def convertData(self, expressionType, expressionRule, fieldName, fieldValue):
        match expressionType:
            case "DATECONVERT":
                return self._convertToDate(
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

    # iso8086 date time validate
    def _convertToDate(self, expressionRule, fieldName, fieldValue, summarise, report_unexpected_exception):
        try:
            convertDate = datetime.datetime.fromisoformat(fieldValue)
            return convertDate.strftime(expressionRule)
        except Exception as e:
            if report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return message

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
