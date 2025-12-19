"""Module containing functions to aid with timeliness checks"""

import datetime


def parse_csv_date(d: str) -> datetime.date:
    return datetime.datetime.strptime(d, "%Y%m%d").date()


def parse_csv_datetime(d: str) -> datetime.datetime:
    """Parses the custom NHS imms batch CSV datetime format YYYYmmddThmmss and an optional 2-digit timezone offset"""
    match len(d):
        case 17:
            return datetime.datetime.strptime(d[0:15], "%Y%m%dT%H%M%S").replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=int(d[15:17])))
            )
        case 15:
            return datetime.datetime.strptime(d, "%Y%m%dT%H%M%S").replace(tzinfo=datetime.timezone.utc)
        case _:
            raise ValueError("Invalid datetime format provided")
