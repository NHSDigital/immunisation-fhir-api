from typing import Any


def make_status(msg: str, status: str = "success") -> dict[str, Any]:
    """Return a simple status dict used by record processing for observability."""
    return {"status": status, "message": msg}
