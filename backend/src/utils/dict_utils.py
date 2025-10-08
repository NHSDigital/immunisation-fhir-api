"""Generic helper module for Python dictionary utility functions"""

from typing import Optional, Any


def get_field(target_dict: dict, *args: str, default: Optional[Any] = None) -> Any:
    """Safely retrieves a value from a dictionary. Supports nested dictionaries."""
    if not target_dict or not isinstance(target_dict, dict):
        return default

    latest_nested_dict = dict(target_dict)

    for key in args:
        if key not in latest_nested_dict:
            return default

        if not isinstance(latest_nested_dict[key], dict):
            return latest_nested_dict[key]

        latest_nested_dict = latest_nested_dict[key]

    return latest_nested_dict
