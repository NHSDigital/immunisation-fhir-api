# Root and base type expression checker functions
import validator.enums.exception_messages as ExceptionMessages
import datetime
import uuid
import re
from validator.lookup.lookup_data import LookUpData
from validator.lookup.key_data import KeyData


class ErrorReport():
    def __init__(self, code: int, message: str, row: int = None, field: str = None, details: str = None,
                 summarise: bool = False):
        self.code = code
        self.message = message
        if not summarise:
            self.row = row
            self.field = field
            self.details = details
        self.summarise = summarise
        # these are set when the error is added to the report
        self.errorGroup = None
        self.name = None
        self.id = None
        self.errorLevel = None

    # function to return the object as a dictionary
    def to_dict(self):
        ret = {
                'code': self.code,
                'message': self.message
            }
        if not self.summarise:
            ret.update({
                'row': self.row,
                'field': self.field,
                'details': self.details
            })
        return ret


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


# main expressions checker
class ExpressionChecker:
    # validation settings
    summarise = False
    report_unexpected_exception = True
    dataParser = any
    dataLookUp = any
    keyData = any

    def __init__(self, dataParser, summarise, report_unexpected_exception):
        self.dataParser = dataParser  # FHIR data parser for additional functions
        self.dataLookUp = LookUpData()  # used for generic look up
        self.keyData = KeyData()  # used for key check on data we know (Snomed / ODS etc)
        self.summarise = summarise
        self.report_unexpected_exception = report_unexpected_exception

    def validateExpression(self, expressionType, rule, fieldName,  fieldValue, row) -> ErrorReport:
        match expressionType:
            case "DATETIME":
                return self._validateDateTime(rule, fieldName, fieldValue, row)
            case "DATE":
                return self._validateDateTime(rule, fieldName, fieldValue, row)
            case "UUID":
                return self._validateUUID(rule, fieldName, fieldValue, row)
            case "INT":
                return self._validateInteger(rule, fieldName, fieldValue, row)
            case "FLOAT":
                return self._validateFloat(rule, fieldName, fieldValue, row)
            case "REGEX":
                return self._validateRegex(rule, fieldName, fieldValue, row)
            case "EQUAL":
                return self._validateEqual(rule, fieldName, fieldValue, row)
            case "NOTEQUAL":
                return self._validateNotEqual(rule, fieldName, fieldValue, row)
            case "IN":
                return self._validateIn(rule, fieldName, fieldValue, row)
            case "NRANGE":
                return self._validateNRange(rule, fieldName, fieldValue, row)
            case "INARRAY":
                return self._validateInArray(rule, fieldName, fieldValue, row)
            case "UPPER":
                return self._validateUpper(rule, fieldName, fieldValue, row)
            case "LOWER":
                return self._validateLower(rule, fieldName, fieldValue, row)
            case "LENGTH":
                return self._validateLength(rule, fieldName, fieldValue, row)
            case "STARTSWITH":
                return self._validateStartsWith(rule, fieldName, fieldValue, row)
            case "ENDSWITH":
                return self._validateEndsWith(rule, fieldName, fieldValue, row)
            case "EMPTY":
                return self._validateEmpty(rule, fieldName, fieldValue, row)
            case "NOTEMPTY":
                return self._validateNotEmpty(rule, fieldName, fieldValue, row)
            case "POSITIVE":
                return self._validatePositive(rule, fieldName, fieldValue, row)
            case "POSTCODE":
                return self._validatePostCode(rule, fieldName, fieldValue, row)
            case "GENDER":
                return self._validateGender(rule, fieldName, fieldValue, row)
            case "NHSNUMBER":
                return self._validateNHSNumber(rule, fieldName, fieldValue, row)
            case "MAXOBJECTS":
                return self._validateMaxObjects(rule, fieldName, fieldValue, row)
            case "ONLYIF":
                return self._validateOnlyIf(rule, fieldName, fieldValue, row)
            case "LOOKUP":
                return self._validateAgainstLookup(rule, fieldName, fieldValue, row)
            case "KEYCHECK":
                return self._validateAgainstKey(rule, fieldName, fieldValue, row)
            case _:
                return "Schema expression not found! Check your expression type : " + expressionType

    # iso8086 date time validate
    def _validateDateTime(self, rule, fieldName,  fieldValue, row):
        try:
            datetime.date.fromisoformat(fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return RecordError(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return RecordError(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # UUID validate
    def _validateUUID(self, expressionRule, fieldName,  fieldValue, row):
        try:
            uuid.UUID(str(fieldValue))
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Integer Validate
    def _validateInteger(self, expressionRule, fieldName,
                         fieldValue, row, summarise) -> ErrorReport:
        try:
            int(fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            if summarise:
                p = RecordError(code, message)
            else:
                p = RecordError(code, message, row, fieldName, details)
            return p
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                if summarise:
                    p = RecordError(ExceptionMessages.UNEXPECTED_EXCEPTION, message)
                else:
                    p = RecordError(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '')
                return p

    #  Float Validate
    def _validateFloat(self, expressionRule, fieldName,  fieldValue, row, summarise):
        try:
            float(fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            if summarise:
                p = {'code': code, 'message': message}
            else:
                p = {'code': code, 'message': message, 'row': row, 'field': fieldName, 'details': details}
            return p
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                if summarise:
                    p = {'code': ExceptionMessages.UNEXPECTED_EXCEPTION, 'message': message}
                else:
                    p = {'code': ExceptionMessages.UNEXPECTED_EXCEPTION, 'message': message,
                         'row': row, 'field': fieldName, 'details': ''}
                return p

    # Length Validate
    def _validateLength(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            strLen = len(fieldValue)
            checklength = int(expressionRule)
            if strLen > checklength:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value length check failed",
                                  "Value is longer than expected")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Regex Validate
    def _validateRegex(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            result = re.search(expressionRule, fieldValue)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED, "String REGEX check failed",
                                  "Value does not meet regex rules")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            if summarise:
                p = ErrorReport(code, message)
            else:
                p = ErrorReport(code, message, row, fieldName, details)
            return p
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                if summarise:
                    p = ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message)
                else:
                    p = ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '')
                return p

    # Equal Validate
    def _validateEqual(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            if fieldValue != expressionRule:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED, "Value equals check failed",
                                  "Value does not equal expected value, Expected- " + expressionRule + " found- "
                                  + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Not Equal Validate
    def _validateNotEqual(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            if fieldValue == expressionRule:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED, "Value not equals check failed",
                                  "Value equals expected value when it should not, Expected- " + expressionRule
                                  + " found- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # In Validate
    def _validateIn(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            if expressionRule.lower() in fieldValue.lower():
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Data not in Value failed", "Check Data not found in Value, List- "
                                  + expressionRule + " Data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # NRange Validate
    def _validateNRange(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            value = float(fieldValue)
            rule = expressionRule.split(",")
            range1 = float(rule[0])
            range2 = float(rule[1])

            if range1 <= value >= range2:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value range check failed", "Value is not within the number range, data- "
                                  + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # InArray Validate
    def _validateInArray(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            ruleList = expressionRule.split(",")

            if fieldValue not in ruleList:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED, "Value not in array check failed",
                                  "Check Value not found in data array")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Upper Validate
    def _validateUpper(self, expressionRule, fieldName, fieldValue, row) -> ErrorReport:
        try:
            result = fieldValue.isupper()

            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value not uppercase", "Check Value not found to be uppercase, value- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    #  Lower Validate
    def _validateLower(self, expressionRule, fieldName,  fieldValue, row) -> ErrorReport:
        try:
            result = fieldValue.islower()

            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value not lowercase",
                                  "Check Value not found to be lowercase, data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Starts With Validate
    def _validateStartsWith(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            result = fieldValue.startswith(expressionRule)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value starts with failure",
                                  "Value does not start as expected, Expected- " + expressionRule
                                  + " found- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Ends With Validate
    def _validateEndsWith(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            result = fieldValue.endswith(expressionRule)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value ends with failure",
                                  "Value does not end as expected, Expected- " + expressionRule
                                  + " found- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Empty Validate
    def _validateEmpty(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            if fieldValue:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value is empty failure",
                                  "Value has data, not as expected, data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Not Empty Validate
    def _validateNotEmpty(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            if not fieldValue:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value not empty failure",
                                  "Value is empty, not as expected")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Positive Validate
    def _validatePositive(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            value = float(fieldValue)
            if value < 0:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value is not positive failure",
                                  "Value is not positive as expected, data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # NHSNumber Validate
    def _validateNHSNumber(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            regexRule = '^6[0-9]{10}$'
            result = re.search(regexRule, fieldValue)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "NHS Number check failed",
                                  "NHS Number does not meet regex rules, data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Gender Validate
    def _validateGender(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            ruleList = ['0', '1', '2', '9']

            if fieldValue not in ruleList:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Gender check failed",
                                  "Gender value not found in array, data- " + fieldValue)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # PostCode Validate
    def _validatePostCode(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            regexRule = '^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y]'
            '[0-9]{1,2})|(([AZa-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) [0-9][A-Za-z]{2})$'
            result = re.search(regexRule, fieldValue)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Postcode check failed",
                                  "Postcode does not meet regex rules")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Max Objects Validate
    def _validateMaxObjects(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            value = len(fieldValue)
            if value > int(expressionRule):
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Max Objects failure",
                                  "Number of objects is greater than expected")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Default to Validate
    def _validateOnlyIf(self, expressionRule, fieldName, fieldValue, row) -> ErrorReport:
        try:
            conversionList = expressionRule.split("|")
            location = conversionList[0]
            valueCheck = conversionList[1]
            dataValue = self.dataParser.getKeyValue(location)

            if (dataValue[0] != valueCheck):
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Validate Only If failure",
                                  "Value was not found at that position")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Check with Lookup
    def _validateAgainstLookup(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            result = self.dataLookUp.findLookUp(fieldValue)
            if not result:
                raise RecordError(ExceptionMessages.RECORD_CHECK_FAILED,
                                  "Value lookup failure",
                                  "Value was not found in Lookup List, Expected- " + fieldValue + " found- nothing")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)

    # Check with Key Lookup
    def _validateAgainstKey(self, expressionRule, fieldName,  fieldValue, row, summarise) -> ErrorReport:
        try:
            result = self.KeyData.findKey(expressionRule, fieldValue)
            if not result:
                raise RecordError(ExceptionMessages.KEY_CHECK_FAILED,
                                  "Key lookup failure",
                                  "Value was not found in Key List, Expected- "
                                  + fieldValue + " found- nothing")
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.KEY_CHECK_FAILED
            message = (e.message if e.message is not None
                       else ExceptionMessages.MESSAGES[ExceptionMessages.KEY_CHECK_FAILED])
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, fieldName, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, fieldName, '', self.summarise)
