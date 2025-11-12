import datetime
import re
import uuid
from typing import Optional

from common.validator.constants.enums import MESSAGES, ExceptionLevels, MessageLabel
from common.validator.error_report.record_error import ErrorReport, RecordError
from common.validator.lookup_expressions.key_data import KeyData
from common.validator.lookup_expressions.lookup_data import LookUpData
from common.validator.validation_utils import check_if_future_date


class ExpressionChecker:
    """
    Validates FHIR and CSV data fields against the expressions defined in the schema
    """

    def __init__(self, data_parser, summarise: bool, report_unexpected_exception: bool):
        self.data_parser = data_parser
        self.data_look_up = LookUpData()
        self.key_data = KeyData()
        self.summarise = summarise
        self.report_unexpected_exception = report_unexpected_exception

    def validate_expression(
        self, expression_type: str, expression_rule: str, field_name: str, field_value: str, row: dict
    ) -> ErrorReport:
        match expression_type:
            case "DATETIME":
                return self._validate_datetime(expression_rule, field_name, field_value, row)
            case "STRING":
                return self._validate_for_string_values(expression_rule, field_name, field_value, row)
            case "LIST":
                return self._validate_for_list_values(expression_rule, field_name, field_value, row)
            case "DATE":
                return self.validate_for_date(expression_rule, field_name, field_value, row)
            case "UUID":
                return self._validate_uuid(expression_rule, field_name, field_value, row)
            case "INT":
                return self._validate_integer(expression_rule, field_name, field_value, row)
            case "FLOAT":
                return self._validate_float(expression_rule, field_name, field_value, row)
            case "REGEX":
                return self._validate_regex(expression_rule, field_name, field_value, row)
            case "EQUAL":
                return self._validate_equal(expression_rule, field_name, field_value, row)
            case "NOTEQUAL":
                return self._validate_not_equal(expression_rule, field_name, field_value, row)
            case "IN":
                return self._validate_in(expression_rule, field_name, field_value, row)
            case "NRANGE":
                return self._validate_n_range(expression_rule, field_name, field_value, row)
            case "INARRAY":
                return self._validate_in_array(expression_rule, field_name, field_value, row)
            case "UPPER":
                return self._validate_upper(expression_rule, field_name, field_value, row)
            case "LOWER":
                return self._validate_lower(expression_rule, field_name, field_value, row)
            case "LENGTH":
                return self._validate_length(expression_rule, field_name, field_value, row)
            case "STARTSWITH":
                return self._validate_starts_with(expression_rule, field_name, field_value, row)
            case "ENDSWITH":
                return self._validate_ends_with(expression_rule, field_name, field_value, row)
            case "EMPTY":
                return self._validate_empty(expression_rule, field_name, field_value, row)
            case "NOTEMPTY":
                return self._validate_not_empty(expression_rule, field_name, field_value, row)
            case "POSITIVE":
                return self._validate_positive(expression_rule, field_name, field_value, row)
            case "POSTCODE":
                return self._validate_post_code(expression_rule, field_name, field_value, row)
            case "GENDER":
                return self._validate_gender(expression_rule, field_name, field_value, row)
            case "NHSNUMBER":
                return self._validate_nhs_number(expression_rule, field_name, field_value, row)
            case "MAXOBJECTS":
                return self._validate_max_objects(expression_rule, field_name, field_value, row)
            case "ONLYIF":
                return self._validate_only_if(expression_rule, field_name, field_value, row)
            case "LOOKUP":
                return self._validate_against_lookup(expression_rule, field_name, field_value, row)
            case "KEYCHECK":
                return self._validate_against_key(expression_rule, field_name, field_value, row)
            case _:
                return "Schema expression not found! Check your expression type : " + expression_type

    # ISO 8601 date/datetime validate (currently date-only)
    def _validate_datetime(self, _expression_rule, field_name, field_value, row) -> ErrorReport:
        try:
            # Current behavior expects date-only; datetime raises and is handled below
            datetime.date.fromisoformat(field_value)
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    def validate_for_date(self, _expression_rule, field_name, field_value, row, future_date_allowed: bool = False):
        """
        Apply pre-validation to a date field to ensure that it is a string (JSON dates must be
        written as strings) containing a valid date in the format "YYYY-MM-DD"
        """
        if not isinstance(field_value, str):
            raise TypeError(f"{field_name} must be a string")

        try:
            parsed_date = datetime.strptime(field_value, "%Y-%m-%d").date()
        except ValueError as value_error:
            raise ValueError(f'{field_name} must be a valid date string in the format "YYYY-MM-DD"') from value_error

        # Enforce future date rule using central checker after successful parse
        if not future_date_allowed and check_if_future_date(parsed_date):
            raise ValueError(f"{field_name} must not be in the future")

    # UUID validate
    def _validate_uuid(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            uuid.UUID(str(field_value))
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Integer Validate
    def _validate_integer(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            int(field_value)
            if expression_rule:
                check_value = int(expression_rule)
                if int(field_value) != check_value:
                    raise RecordError(
                        ExceptionLevels.RECORD_CHECK_FAILED,
                        "Value integer check failed",
                        MessageLabel.VALUE_MISMATCH_MSG
                        + MessageLabel.EXPECTED_LABEL
                        + expression_rule
                        + " "
                        + MessageLabel.FOUND_LABEL
                        + field_value,
                    )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Length Validate
    def _validate_length(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            str_len = len(field_value)
            check_length = int(expression_rule)
            if str_len > check_length:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED, "Value length check failed", "Value is longer than expected"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Regex Validate
    def _validate_regex(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = re.search(expression_rule, field_value)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "String REGEX check failed",
                    "Value does not meet regex rules",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Equal Validate
    def _validate_equal(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            if field_value != expression_rule:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value equals check failed",
                    MessageLabel.VALUE_MISMATCH_MSG
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    def for_list(self, expression_rule: str, field_name: str, field_value: list, row: dict):
        """
        Apply validation to a list field to ensure it is a non-empty list which meets the length requirements and
        requirements, if applicable, for each list element to be a non-empty string or non-empty dictionary
        """
        defined_length: Optional[int] = (None,)
        max_length: Optional[int] = (None,)
        elements_are_strings: bool = (False,)
        string_element_max_length: Optional[int] = (None,)
        elements_are_dicts: bool = (False,)
        if not isinstance(field_value, list):
            raise TypeError(f"{field_name} must be an array")

        if defined_length:
            if len(field_value) != defined_length:
                raise ValueError(f"{field_name} must be an array of length {defined_length}")
        else:
            if len(field_value) == 0:
                raise ValueError(f"{field_name} must be a non-empty array")

        if max_length is not None and len(field_value) > max_length:
            raise ValueError(f"{field_name} must be an array of maximum length {max_length}")

        if elements_are_strings:
            for idx, element in enumerate(field_value):
                self._validate_for_string_values.for_string(
                    element, f"{field_name}[{idx}]", max_length=string_element_max_length
                )

        if elements_are_dicts:
            for element in field_value:
                if not isinstance(element, dict):
                    raise TypeError(f"{field_name} must be an array of objects")
                if len(element) == 0:
                    raise ValueError(f"{field_name} must be an array of non-empty objects")

    # Not Equal Validate
    def _validate_not_equal(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            if field_value == expression_rule:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value not equals check failed",
                    "Value equals expected value when it should not, Expected- "
                    + expression_rule
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # In Validate
    def _validate_in(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            if expression_rule.lower() not in field_value.lower():
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Data not in Value failed",
                    "Check Data not found in Value, List- " + expression_rule + " Data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # NRange Validate
    def _validate_n_range(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            value = float(field_value)
            rule = expression_rule.split(",")
            range1 = float(rule[0])
            range2 = float(rule[1])

            if not (range1 <= value <= range2):
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value range check failed",
                    "Value is not within the number range, data- " + field_value,
                )
            return None
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # InArray Validate
    def _validate_in_array(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            rule_list = expression_rule.split(",")

            if field_value not in rule_list:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value not in array check failed",
                    "Check Value not found in data array",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Upper Validate
    def _validate_upper(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = field_value.isupper()

            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value not uppercase",
                    "Check Value not found to be uppercase, value- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    #  Lower Validate
    def _validate_lower(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = field_value.islower()

            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value not lowercase",
                    "Check Value not found to be lowercase, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Starts With Validate
    def _validate_starts_with(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = field_value.startswith(expression_rule)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value starts with failure",
                    "Value does not start as expected, "
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Ends With Validate
    def _validate_ends_with(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = field_value.endswith(expression_rule)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value ends with failure",
                    "Value does not end as expected, "
                    + MessageLabel.EXPECTED_LABEL
                    + expression_rule
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Empty Validate
    def _validate_empty(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            if field_value:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value is empty failure",
                    "Value has data, not as expected, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # String Pre-Validation
    def _validate_for_string_values(
        self, _expression_rule: str, field_name: str, field_value: str, row: dict
    ) -> ErrorReport:
        """
        Apply validation to a string field to ensure it is a non-empty string which meets
        the length requirements and predefined values requirements
        """
        defined_length: int = (10,)
        max_length: int = (None,)
        predefined_values: list = (None,)
        spaces_allowed: bool = False
        try:
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be a string")

            if field_value.isspace():
                raise ValueError(f"{field_name} must be a non-empty string")

            if defined_length:
                if len(field_value) != defined_length:
                    raise ValueError(f"{field_name} must be {defined_length} characters")
            else:
                if len(field_value) == 0:
                    raise ValueError(f"{field_name} must be a non-empty string")

            if max_length:
                if len(field_value) > max_length:
                    raise ValueError(f"{field_name} must be {max_length} or fewer characters")
            if predefined_values:
                if field_value not in predefined_values:
                    raise ValueError(f"{field_name} must be one of the following: " + str(", ".join(predefined_values)))

            if not spaces_allowed:
                if " " in field_value:
                    raise ValueError(f"{field_name} must not contain spaces")
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Not Empty Validate
    def _validate_not_empty(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            if not field_value:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED, "Value not empty failure", "Value is empty, not as expected"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Positive Validate
    def _validate_positive(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            value = float(field_value)
            if value < 0:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value is not positive failure",
                    "Value is not positive as expected, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # NHSNumber Validate
    def _validate_nhs_number(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            regex_rule = r"^6\d{10}$"
            result = re.search(regex_rule, field_value)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "NHS Number check failed",
                    "NHS Number does not meet regex rules, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Gender Validate
    def _validate_gender(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            rule_list = ["0", "1", "2", "9"]

            if field_value not in rule_list:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Gender check failed",
                    "Gender value not found in array, data- " + field_value,
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # PostCode Validate
    def _validate_post_code(self, _expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            # UK postcode regex (allows optional space)
            regex_rule = r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
            result = re.search(regex_rule, field_value)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED, "Postcode check failed", "Postcode does not meet regex rules"
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Max Objects Validate
    def _validate_max_objects(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            value = len(field_value)
            if value > int(expression_rule):
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Max Objects failure",
                    "Number of objects is greater than expected",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Default to Validate
    def _validate_only_if(self, expression_rule: str, field_name: str, _field_value: str, row: dict) -> ErrorReport:
        try:
            conversion_list = expression_rule.split("|")
            location = conversion_list[0]
            value_check = conversion_list[1]
            data_value = self.data_parser.get_key_value(location)

            if data_value[0] != value_check:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Validate Only If failure",
                    "Value was not found at that position",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Check with Lookup
    def _validate_against_lookup(
        self, _expression_rule: str, field_name: str, field_value: str, row: dict
    ) -> ErrorReport:
        try:
            result = self.data_look_up.find_lookup(field_value)
            if not result:
                raise RecordError(
                    ExceptionLevels.RECORD_CHECK_FAILED,
                    "Value lookup failure",
                    "Value was not found in Lookup List, "
                    + MessageLabel.EXPECTED_LABEL
                    + field_value
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + "nothing",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.RECORD_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)

    # Check with Key Lookup
    def _validate_against_key(self, expression_rule: str, field_name: str, field_value: str, row: dict) -> ErrorReport:
        try:
            result = self.key_data.find_key(expression_rule, field_value)
            if not result:
                raise RecordError(
                    ExceptionLevels.KEY_CHECK_FAILED,
                    "Key lookup failure",
                    "Value was not found in Key List, "
                    + MessageLabel.EXPECTED_LABEL
                    + field_value
                    + " "
                    + MessageLabel.FOUND_LABEL
                    + "nothing",
                )
        except RecordError as e:
            code = e.code if e.code is not None else ExceptionLevels.KEY_CHECK_FAILED
            message = e.message if e.message is not None else MESSAGES[ExceptionLevels.KEY_CHECK_FAILED]
            if e.details is not None:
                details = e.details
            return ErrorReport(code, message, row, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, row, field_name, "", self.summarise)
