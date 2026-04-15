from enum import StrEnum


class ApiOperationCode(StrEnum):
    CREATE = "c"
    READ = "r"
    UPDATE = "u"
    DELETE = "d"
    SEARCH = "s"
