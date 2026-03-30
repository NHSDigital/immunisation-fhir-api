from typing import Any, NotRequired, TypedDict


class OperationOutcomeDict(TypedDict):
    record: str
    operation_type: str
    statusCode: str
    statusDesc: str
    diagnostics: NotRequired[Any]
