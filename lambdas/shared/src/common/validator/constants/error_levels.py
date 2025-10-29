# all error Levels
from enum import IntEnum


class ErrorLevels(IntEnum):
    CRITICAL_ERROR = 0
    WARNING = 1
    NOTIFICATION = 2


MESSAGES = {
    ErrorLevels.CRITICAL_ERROR: "Critical Validation Error [%s]: %s",
    ErrorLevels.WARNING: "Non-Critical Validation Error [%s]: %s",
    ErrorLevels.NOTIFICATION: "Quality Issue Found [%s]: %s",
}
