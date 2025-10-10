from typing import Any, Dict


def make_status(msg: str, nhs_number: str | None = None, status: str = "success") -> Dict[str, Any]:
    """Return a simple status dict used by record processing for observability.

    If `nhs_number` is None the key is omitted which keeps the output shape
    compatible with callers that expect only a status/message.
    """
    result = {"status": status, "message": msg}
    if nhs_number is not None:
        result["nhs_number"] = nhs_number
    return result
