# Root and base type expression checker functions
import datetime
import re
import uuid
from enum import Enum
from enum import StrEnum

import common.validator.enums.exception_messages as ExceptionMessages
from common.validator.lookup_expressions.key_data import KeyData
from common.validator.lookup_expressions.lookup_data import LookUpData
from common.validator.record_error import ErrorReport
from common.validator.record_error import RecordError


class ExpressionType(Enum):
    DATETIME = "DATETIME"
    DATE = "DATE"
    UUID = "UUID"
    INT = "INT"
    FLOAT = "FLOAT"
    REGEX = "REGEX"
    EQUAL = "EQUAL"
    NOTEQUAL = "NOTEQUAL"
    IN = "IN"
    NRANGE = "NRANGE"
    INARRAY = "INARRAY"
    UPPER = "UPPER"
    LOWER = "LOWER"
    LENGTH = "LENGTH"
    STARTSWITH = "STARTSWITH"
    ENDSWITH = "ENDSWITH"
    EMPTY = "EMPTY"
    NOTEMPTY = "NOTEMPTY"
    POSITIVE = "POSITIVE"
    GENDER = "GENDER"
    NHSNUMBER = "NHSNUMBER"
    MAXOBJECTS = "MAXOBJECTS"
    POSTCODE = "POSTCODE"
    ONLYIF = "ONLYIF"
    LOOKUP = "LOOKUP"
    KEYCHECK = "KEYCHECK"


class MessageLabel(StrEnum):
    EXPECTED_LABEL = "Expected- "
    FOUND_LABEL = "Found- "
    VALUE_MISMATCH_MSG = "Value does not equal expected value, "


class ExpressionChecker:
    def __init__(self, data_parser, summarise, report_unexpected_exception):
        self.data_parser = data_parser  # FHIR data parser for additional functions
        self.data_look_up = LookUpData()  # used for generic look up
        self.key_data = KeyData()  # used for key check on data we know (Snomed / ODS etc)
        self.summarise = summarise
        self.report_unexpected_exception = report_unexpected_exception

    def validate_expression(self, expression_type: str, rule, field_name, field_value, row) -> ErrorReport:
        match expression_type:
            case "DATETIME":
                return self._validate_datetime(rule, field_name, field_value, row)
            case "DATE":
                return self._validate_datetime(rule, field_name, field_value, row)
            case "UUID":
                return self._validate_uuid(rule, field_name, field_value, row)
            case "INT":
                return self._validate_integer(rule, field_name, field_value, row)
            case "FLOAT":
                return self._validate_float(rule, field_name, field_value, row)
            case "REGEX":
                return self._validate_regex(rule, field_name, field_value, row)
            case "EQUAL":
                return self._validate_equal(rule, field_name, field_value, row)
            case "NOTEQUAL":
                return self._validate_not_equal(rule, field_name, field_value, row)
            case "IN":
                return self._validate_in(rule, field_name, field_value, row)
            case "NRANGE":
                return self._validate_n_range(rule, field_name, field_value, row)
            case "INARRAY":
                return self._validate_in_array(rule, field_name, field_value, row)
            case "UPPER":
                return self._validate_upper(rule, field_name, field_value, row)
            case "LOWER":
                return self._validate_lower(rule, field_name, field_value, row)
            case "LENGTH":
                return self._validate_length(rule, field_name, field_value, row)
            case "STARTSWITH":
                return self._validate_starts_with(rule, field_name, field_value, row)
            case "ENDSWITH":
                return self._validate_ends_with(rule, field_name, field_value, row)
            case "EMPTY":
                return self._validate_empty(rule, field_name, field_value, row)
            case "NOTEMPTY":
                return self._validate_not_empty(rule, field_name, field_value, row)
            case "POSITIVE":
                return self._validate_positive(rule, field_name, field_value, row)
            case "POSTCODE":
                return self._validate_post_code(rule, field_name, field_value, row)
            case "GENDER":
                return self._validate_gender(rule, field_name, field_value, row)
            case "NHSNUMBER":
                return self._validate_nhs_number(rule, field_name, field_value, row)
            case "MAXOBJECTS":
                return self._validate_max_objects(rule, field_name, field_value, row)
            case "ONLYIF":
                return self._validate_only_if(rule, field_name, field_value, row)
            case "LOOKUP":
                return self._validate_against_lookup(rule, field_name, field_value, row)
            case "KEYCHECK":
                return self._validate_against_key(rule, field_name, field_value, row)
            case _:
                return "Schema expression not found! Check your expression type : " + expression_type

    # ISO 8601 date/datetime validate (currently date-only)
    def _validate_datetime(self, rule, field_name, field_value, row) -> ErrorReport:
        try:
            datetime.date.fromisoformat(field_value)
            # rule is not used - could be date only, date time, past, future etc
            if rule:
                pass

        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # UUID validate
    def _validate_uuid(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            uuid.UUID(str(field_value))
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Integer Validate
    def _validate_integer(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            int(field_value)
            if expression_rule:
                # TODO - code is incomplete here. It appears there should be a check
                # against expression_rule but it's not implemented. eg max, min, equal etc
                # eg "1" means value must be 1
                # "1:10" means value must be between 1 to 10
                # "1,10" means value must be either 1 or 10
                # ":10" means value must be less than or equal to 10
                # "1:" means value must be greater than or equal to 1
                # ">10" means value must be greater than 10
                # "<10" means value must be less than 10

                check_value = int(expression_rule)
                if int(field_value) != check_value:
                    raise RecordError(
                        ExceptionMessages.RECORD_CHECK_FAILED,
                        "Value integer check failed",
                        "Value does not equal expected value, "
                        + MessageLabel.EXPECTED_LABEL
                        + expression_rule
                        + " "
                        + MessageLabel.FOUND_LABEL
                        + field_value,
                    )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    #  Float Validate
    def _validate_float(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            float(field_value)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Length Validate
    def _validate_length(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            str_len = len(field_value)
            check_length = int(expression_rule)
            if str_len > check_length:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED, "Value length check failed", "Value is longer than expected"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Regex Validate
    def _validate_regex(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = re.search(expression_rule, field_value)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "String REGEX check failed",
                    "Value does not meet regex rules",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Equal Validate
    def _validate_equal(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            if field_value != expression_rule:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value equals check failed",
                    "Value does not equal expected value, "
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Not Equal Validate
    def _validate_not_equal(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            if field_value == expression_rule:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value not equals check failed",
                    "Value equals expected value when it should not, Expected- "
                    + expression_rule
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # In Validate
    def _validate_in(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            if expression_rule.lower() not in field_value.lower():
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Data not in Value failed",
                    "Check Data not found in Value, List- " + expression_rule + " Data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # NRange Validate
    def _validate_n_range(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            value = float(field_value)
            rule = expression_rule.split(",")
            range1 = float(rule[0])
            range2 = float(rule[1])

            if not (range1 <= value <= range2):
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value range check failed",
                    "Value is not within the number range, data- " + field_value,
                )
            return None
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # InArray Validate
    def _validate_in_array(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            rule_list = expression_rule.split(",")

            if field_value not in rule_list:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value not in array check failed",
                    "Check Value not found in data array",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Upper Validate
    def _validate_upper(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = field_value.isupper()

            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value not uppercase",
                    "Check Value not found to be uppercase, value- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    #  Lower Validate
    def _validate_lower(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = field_value.islower()

            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value not lowercase",
                    "Check Value not found to be lowercase, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Starts With Validate
    def _validate_starts_with(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = field_value.startswith(expression_rule)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value starts with failure",
                    "Value does not start as expected, "
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Ends With Validate
    def _validate_ends_with(self, expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = field_value.endswith(expression_rule)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value ends with failure",
                    "Value does not end as expected, "
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Empty Validate
    def _validate_empty(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            if field_value:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value is empty failure",
                    "Value has data, not as expected, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Not Empty Validate
    def _validate_not_empty(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            if not field_value:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED, "Value not empty failure", "Value is empty, not as expected"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Positive Validate
    def _validate_positive(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            value = float(field_value)
            if value < 0:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value is not positive failure",
                    "Value is not positive as expected, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # NHSNumber Validate
    def _validate_nhs_number(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            regexRule = "^6[0-9]{10}$"
            result = re.search(regexRule, field_value)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "NHS Number check failed",
                    "NHS Number does not meet regex rules, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Gender Validate
    def _validate_gender(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            ruleList = ["0", "1", "2", "9"]

            if field_value not in ruleList:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Gender check failed",
                    "Gender value not found in array, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # PostCode Validate
    def _validate_post_code(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            # UK postcode regex (allows optional space)
            regexRule = r"^(GIR\s?0AA|(?:(?:[A-PR-UWYZ][0-9]{1,2})|(?:[A-PR-UWYZ][A-HK-Y][0-9]{1,2})|(?:[A-PR-UWYZ][0-9][A-HJKS-UW])|(?:[A-PR-UWYZ][A-HK-Y][0-9][ABEHMNPRV-Y]))\s?[0-9][ABD-HJLNP-UW-Z]{2})$"
            result = re.search(regexRule, field_value)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED, "Postcode check failed", "Postcode does not meet regex rules"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Max Objects Validate
    def _validate_max_objects(self, expressionRule, field_name, field_value, row) -> ErrorReport:
        try:
            value = len(field_value)
            if value > int(expressionRule):
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Max Objects failure",
                    "Number of objects is greater than expected",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Default to Validate
    def _validate_only_if(self, expressionRule, field_name, field_value, row) -> ErrorReport:
        try:
            conversionList = expressionRule.split("|")
            location = conversionList[0]
            valueCheck = conversionList[1]
            dataValue = self.data_parser.get_key_value(location)

            if dataValue[0] != valueCheck:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Validate Only If failure",
                    "Value was not found at that position",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Check with Lookup
    def _validate_against_lookup(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            result = self.data_look_up.find_lookup(field_value)
            if not result:
                raise RecordError(
                    ExceptionMessages.RECORD_CHECK_FAILED,
                    "Value lookup failure",
                    "Value was not found in Lookup List, "
                    + MessageLabel.EXPECTED_LABEL
                    + field_value
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + "nothing",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.RECORD_CHECK_FAILED
            message = (
                e.message
                if e.message is not None
                else ExceptionMessages.MESSAGES[ExceptionMessages.RECORD_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Check with Key Lookup
    def _validate_against_key(self, expressionRule, field_name, field_value, row) -> ErrorReport:
        try:
            result = self.key_data.findKey(expressionRule, field_value)
            if not result:
                raise RecordError(
                    ExceptionMessages.KEY_CHECK_FAILED,
                    "Key lookup failure",
                    "Value was not found in Key List, "
                    + MessageLabel.EXPECTED_LABEL
                    + field_value
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + "nothing",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionMessages.KEY_CHECK_FAILED
            message = (
                e.message if e.message is not None else ExceptionMessages.MESSAGES[ExceptionMessages.KEY_CHECK_FAILED]
            )
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = ExceptionMessages.MESSAGES[ExceptionMessages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionMessages.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)
