import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from common.validator.constants.enums import MESSAGES, ExceptionLevels, MessageLabel
from common.validator.error_report.record_error import ErrorReport, RecordError
from common.validator.expression_rule import expression_rule_per_field
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
        self, expression_type: str, expression_rule: str, field_name: str, field_value: str, row: dict = None
    ) -> ErrorReport:
        match expression_type:
            case "STRING":
                return self.validation_for_string_values(expression_rule, field_name, field_value)
            case "LIST":
                return self.validation_for_list(expression_rule, field_name, field_value)
            case "DATE":
                return self.validation_for_date(expression_rule, field_name, field_value)
            case "DATETIME":
                return self.validation_for_date_time(expression_rule, field_name, field_value)
            case "POSITIVEINTEGER":
                return self.validation_for_positive_integer(expression_rule, field_name, field_value)
            case "UNIQUELIST":
                return self.validation_for_unique_list(expression_rule, field_name, field_value)
            case "BOOLEAN":
                return self.validation_for_boolean(expression_rule, field_name, field_value)
            case "INTDECIMAL":
                return self.validation_for_integer_or_decimal(expression_rule, field_name, field_value)
            case "POSTCODE":
                return self._validate_post_code(expression_rule, field_name, field_value)
            case "GENDER":
                return self._validate_gender(expression_rule, field_name, field_value)
            case _:
                return "Schema expression not found! Check your expression type : " + expression_type

    # ISO 8601 date/datetime validate (currently date-only)
    def validation_for_date(self, _expression_rule, field_name, field_value):
        """
        Apply pre-validation to a date field to ensure that it is a string (JSON dates must be
        written as strings) containing a valid date in the format "YYYY-MM-DD"
        """
        try:
            future_date_allowed: bool = False
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be a string")

            try:
                parsed_date = datetime.strptime(field_value, "%Y-%m-%d").date()
            except ValueError as value_error:
                raise ValueError(f'{field_name} must be a valid date string in the format "YYYY-MM-DD"') from value_error

            # Enforce future date rule using central checker after successful parse
            if not future_date_allowed and check_if_future_date(parsed_date):
                raise ValueError(f"{field_name} must not be in the future")
        except (TypeError, ValueError) as e:
            code = ExceptionLevels.RECORD_CHECK_FAILED
            message = MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            details = str(e)
            return ErrorReport(code, message, None, field_name, details)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, None, field_name)

    def validation_for_positive_integer(self, _expression_rule, field_name, field_value, row):
        """
        Apply pre-validation to an integer field to ensure that it is a positive integer,
        which does not exceed the maximum allowed value (if applicable)
        """
        max_value: int = None
        # This check uses type() instead of isinstance() because bool is a subclass of int.
        if type(field_value) is not int:  # pylint: disable=unidiomatic-typecheck
            raise TypeError(f"{field_name} must be a positive integer")

        if field_value <= 0:
            raise ValueError(f"{field_name} must be a positive integer")

        if max_value:
            if field_value > max_value:
                raise ValueError(f"{field_name} must be an integer in the range 1 to {max_value}")

    def validation_for_integer_or_decimal(
        self, _expression_rule, field_value: Union[int, Decimal], field_name: str, row: dict
    ):
        """
        Apply pre-validation to a decimal field to ensure that it is an integer or decimal,
        which does not exceed the maximum allowed number of decimal places (if applicable)
        """
        if not (
            # This check uses type() instead of isinstance() because bool is a subclass of int.
            type(field_value) is int  # pylint: disable=unidiomatic-typecheck
            or type(field_value) is Decimal  # pylint: disable=unidiomatic-typecheck
        ):
            raise TypeError(f"{field_name} must be a number")

    def validation_for_unique_list(
        list_to_check: list,
        unique_value_in_list: str,
        field_location: str,
    ):
        """
        Apply pre-validation to a list of dictionaries to ensure that a specified value in each
        dictionary is unique across the list
        """
        found = []
        for item in list_to_check:
            if item[unique_value_in_list] in found:
                raise ValueError(
                    f"{field_location.replace('FIELD_TO_REPLACE', item[unique_value_in_list])}" + " must be unique"
                )

            found.append(item[unique_value_in_list])

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

    def validation_for_boolean(self, expression_rule: str, field_name: str, field_value: str, row: dict):
        """Apply pre-validation to a boolean field to ensure that it is a boolean"""
        if not isinstance(field_value, bool):
            raise TypeError(f"{field_name} must be a boolean")

    def validation_for_list(self, expression_rule: str, field_name: str, field_value: list):
        """
        Apply validation to a list field to ensure it is a non-empty list which meets the length requirements and
        requirements, if applicable, for each list element to be a non-empty string or non-empty dictionary
        """
        rules = expression_rule_per_field(expression_rule) if expression_rule else {}
        defined_length: Optional[int] = rules.get("defined_length", None)
        max_length: Optional[int] = rules.get("max_length", None)
        elements_are_strings: bool = rules.get("elements_are_strings", False)
        string_element_max_length: Optional[int] = rules.get("string_element_max_length", None)
        elements_are_dicts: bool = rules.get("elements_are_dicts", False)

        try:
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
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, field_name)

    def validation_for_date_time(
        self, expression_rule: str, field_name: str, field_value: str, row: dict, strict_timezone: bool = True
    ):
        """
        Apply pre-validation to a datetime field to ensure that it is a string (JSON dates must be written as strings)
        containing a valid datetime. Note that partial dates are valid for FHIR, but are not allowed for this API.
        Valid formats are any of the following:
        * 'YYYY-MM-DD' - Full date only
        * 'YYYY-MM-DDThh:mm:ss%z' - Full date, time without milliseconds, timezone
        * 'YYYY-MM-DDThh:mm:ss.f%z' - Full date, time with milliseconds (any level of precision), timezone
        """

        if not isinstance(field_value, str):
            raise TypeError(f"{field_name} must be a string")

        error_message = (
            f"{field_name} must be a valid datetime in one of the following formats:"
            "- 'YYYY-MM-DD' — Full date only"
            "- 'YYYY-MM-DDThh:mm:ss%z' — Full date and time with timezone (e.g. +00:00 or +01:00)"
            "- 'YYYY-MM-DDThh:mm:ss.f%z' — Full date and time with milliseconds and timezone"
            "-  Date must not be in the future."
        )
        if strict_timezone:
            error_message += (
                "Only '+00:00' and '+01:00' are accepted as valid timezone offsets.\n"
                f"Note that partial dates are not allowed for {field_name} in this service.\n"
            )

        allowed_suffixes = {
            "+00:00",
            "+01:00",
            "+0000",
            "+0100",
        }

        # List of accepted strict formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ]

        for fmt in formats:
            try:
                fhir_date = datetime.strptime(field_value, fmt)
                # Enforce future-date rule using central checker after successful parse
                if check_if_future_date(fhir_date):
                    raise ValueError(f"{field_name} must not be in the future")
                # After successful parse, enforce timezone and future-date rules
                if strict_timezone and fhir_date.tzinfo is not None:
                    if not any(field_value.endswith(suffix) for suffix in allowed_suffixes):
                        raise ValueError(error_message)
                return fhir_date.isoformat()
            except ValueError:
                continue

        raise ValueError(error_message)

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
    def validation_for_string_values(self, expression_rule: str, field_name: str, field_value: str) -> ErrorReport:
        """
        Apply validation to a string field to ensure it is a non-empty string which meets
        the length requirements and predefined values requirements
        """

        rules = expression_rule_per_field(expression_rule) if expression_rule else {}
        defined_length = rules.get("defined_length", None)
        max_length = rules.get("max_length", None)
        predefined_values = rules.get("predefined_values", None)
        spaces_allowed = rules.get("spaces_allowed", None)

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
        except (ValueError, TypeError) as e:
            code = ExceptionLevels.RECORD_CHECK_FAILED
            message = MESSAGES[ExceptionLevels.RECORD_CHECK_FAILED]
            details = str(e)
            return ErrorReport(code, message, None, field_name, details)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, None, field_name)

    # Not Empty Validate
    def _validate_not_empty(self, _expression_rule: str, field_name: str, field_value: str) -> ErrorReport:
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
            return ErrorReport(code, message, None, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, None, field_name)

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
            return ErrorReport(code, message, None, field_name, details, self.summarise)
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
    def _validate_gender(self, _expression_rule: str, field_name: str, field_value: str) -> ErrorReport:
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
            return ErrorReport(code, message, None, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, None, field_name)

    # PostCode Validate
    def _validate_post_code(self, _expression_rule: str, field_name: str, field_value: str) -> ErrorReport:
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
            return ErrorReport(code, message, None, field_name, details, self.summarise)
        except Exception as e:
            if self.report_unexpected_exception:
                message = MESSAGES[ExceptionLevels.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, e)
                return ErrorReport(ExceptionLevels.UNEXPECTED_EXCEPTION, message, None, field_name, "", self.summarise)
