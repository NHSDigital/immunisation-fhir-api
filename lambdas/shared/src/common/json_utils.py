from ast import Dict
from typing import Any


def get_field_or_none(record: Dict[str, Any], field_name: str) -> Any:
    """Return field value or None if field doesn't exist"""
    return record.get(field_name)
