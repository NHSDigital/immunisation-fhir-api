from datetime import datetime, timedelta, timezone

def format_timestamp(timestamp):
    parts = timestamp.split(".")

    if len(parts) == 2:
        milliseconds, timezone = parts[1].split("+")
        milliseconds = milliseconds.ljust(6, "0")
        
        return f"{parts[0]}.{milliseconds}+{timezone}"
    
def covert_to_expected_date_format(date_string: str) -> str:
    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.isoformat()
    except ValueError:
        return "Invalid format"

    
def iso_to_compact(dt_str):
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt.strftime("%Y%m%dT%H%M%S00")


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def generate_date(date_str: str) -> str:
    now = datetime.now(timezone.utc)
    match date_str:
        case "future_occurrence":
            return (now + timedelta(seconds=500)).isoformat(timespec='milliseconds')
        case "past_occurrence":
            return (now - timedelta(seconds=5050)).isoformat(timespec='milliseconds')
        case "current_occurrence_with_milliseconds":
            now = now  - timedelta(seconds=50)
            return now.strftime("%Y%m%dT%H%M%S") + "00"
        case "invalid_batch_occurrence":
            return now.isoformat(timespec='milliseconds')
        case "current_occurrence":
            return (now - timedelta(seconds=60)).isoformat(timespec='milliseconds')
        case "current_date":
            return str(now.date())
        case "future_date":
            return str((now + timedelta(days=1)).date())
        case "past_date":
            return str((now - timedelta(days=1)).date())
        case "invalid_format":
            return "2023/23/01"
        case "nonexistent":
            return "2023-02-30T10:00:00.000Z"
        case "empty":
            return ""
        case "none":
            return None
        case _:
            raise ValueError(f"Unknown date type: {date_str}")
        
def format_date_yyyymmdd(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {date_str}") from e
