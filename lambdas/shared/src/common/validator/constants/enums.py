from enum import IntEnum
from enum import StrEnum


# Used for error report messages in DQ Reporter to categorize error levels
class ErrorLevels(IntEnum):
    CRITICAL_ERROR = 0
    WARNING = 1
    NOTIFICATION = 2


MESSAGES = {
    ErrorLevels.CRITICAL_ERROR: "Critical Validation Error [%s]: %s",
    ErrorLevels.WARNING: "Non-Critical Validation Error [%s]: %s",
    ErrorLevels.NOTIFICATION: "Quality Issue Found [%s]: %s",
}


# Constants for error report messages used in Expression Checker
class MessageLabel(StrEnum):
    EXPECTED_LABEL = "Expected- "
    FOUND_LABEL = "Found- "
    VALUE_MISMATCH_MSG = "Value does not equal expected value, "


class ExceptionLevels(IntEnum):
    UNEXPECTED_EXCEPTION = 0
    VALUE_CHECK_FAILED = 1
    HEADER_CHECK_FAILED = 2
    RECORD_LENGTH_CHECK_FAILED = 3
    VALUE_PREDICATE_FALSE = 4
    RECORD_CHECK_FAILED = 5
    RECORD_PREDICATE_FALSE = 6
    UNIQUE_CHECK_FAILED = 7
    ASSERT_CHECK_FAILED = 8
    FINALLY_ASSERT_CHECK_FAILED = 9
    PARSING_ERROR = 10
    PARENT_FAILED = 11
    KEY_CHECK_FAILED = 12


MESSAGES = {
    ExceptionLevels.UNEXPECTED_EXCEPTION: "Unexpected exception [%s]: %s",
    ExceptionLevels.VALUE_CHECK_FAILED: "Value Check Failed [%s]: %s",
    ExceptionLevels.HEADER_CHECK_FAILED: "Header Check Failed [%s]: %s",
    ExceptionLevels.RECORD_LENGTH_CHECK_FAILED: "Record Length Check Failed [%s]: %s",
    ExceptionLevels.RECORD_CHECK_FAILED: "Record Check Failed [%s]: %s",
    ExceptionLevels.VALUE_PREDICATE_FALSE: "Value Predicate False [%s]: %s",
    ExceptionLevels.RECORD_PREDICATE_FALSE: "Record Predicate False [%s]: %s",
    ExceptionLevels.UNIQUE_CHECK_FAILED: "Unique Check Failed [%s]: %s",
    ExceptionLevels.ASSERT_CHECK_FAILED: "Assert Check Failed [%s]: %s",
    ExceptionLevels.FINALLY_ASSERT_CHECK_FAILED: "Finally Assert Check Failed [%s]: %s",
    ExceptionLevels.PARSING_ERROR: "Parsing Error [%s]: %s",
    ExceptionLevels.PARENT_FAILED: "Parent Failed [%s]: %s",
    ExceptionLevels.KEY_CHECK_FAILED: "Key Check Failed [%s]: %s",
}


class DataType(StrEnum):
    FHIR = "FHIR"
    FHIRJSON = "FHIRJSON"
    CSV = "CSV"
    CSVROW = "CSVROW"
