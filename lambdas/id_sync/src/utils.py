from typing import Any, Dict


def make_status(msg: str, status: str = "success") -> Dict[str, Any]:
    """Return a simple status dict used by record processing for observability."""
    return {"status": status, "message": msg}
