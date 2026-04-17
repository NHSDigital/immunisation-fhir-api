from datetime import datetime, timedelta, timezone

from common.constants import ALLOWED_OFFSET_SUFFIXES


def timestamp_to_rfc3339(value: str, field_name: str = "DATE_AND_TIME") -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value:
        raise ValueError(f"{field_name} is required")

    offset_suffix = value[-2:]
    if offset_suffix not in ALLOWED_OFFSET_SUFFIXES:
        raise ValueError(f"{field_name} timezone suffix must be 00 or 01")

    try:
        parsed_date = datetime.strptime(value[:-2], "%Y%m%dT%H%M%S")
    except ValueError as e:
        raise ValueError(f"{field_name} must contain a valid compact timestamp") from e

    tz = timezone(timedelta(hours=int(offset_suffix)))
    return parsed_date.replace(tzinfo=tz).isoformat(timespec="seconds").replace("+00:00", "Z")
