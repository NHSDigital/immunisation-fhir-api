"""Module containing functions to aid with timeliness checks"""

import datetime
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class TimelinessCheckOutput:
    """
    The required outputs for the data quality team for timeliness checks.

    recorded_timeliness_days - the number of days between the vaccination taking place and being recorded into the
    clinical system

    ingested_timeliness_seconds - the seconds between the vaccination taking place and the record being provided to the
    Immunisation FHIR API/batch processor for ingestion
    """

    recorded_timeliness_days: Optional[int]
    ingested_timeliness_seconds: Optional[int]


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


def get_recorded_date_from_immunisation(immunization: dict) -> Optional[datetime.date]:
    try:
        parsed_recorded_date = parse_csv_date(immunization.get("RECORDED_DATE"))
    except ValueError:
        # Completeness and validity checks will catch these issues separately
        return None

    return parsed_recorded_date


def get_occurrence_datetime_from_immunisation(immunization: dict) -> Optional[datetime.datetime]:
    try:
        parsed_recorded_date = parse_csv_datetime(immunization.get("DATE_AND_TIME"))
    except ValueError:
        # Completeness and validity checks will catch these issues separately
        return None

    return parsed_recorded_date


def get_recorded_timeliness_days(immunisation: dict) -> Optional[int]:
    """Gets the time delta in days between the recorded date and occurrence date. Returns None is either of the fields
    are not provided or are invalid dates."""
    recorded_date = get_recorded_date_from_immunisation(immunisation)
    occurrence_date_time = get_occurrence_datetime_from_immunisation(immunisation)

    if recorded_date is None or occurrence_date_time is None:
        return None

    occurrence_date = datetime.date(occurrence_date_time.year, occurrence_date_time.month, occurrence_date_time.day)

    return (recorded_date - occurrence_date).days


def get_ingested_timeliness_seconds(immunisation: dict, datetime_now: datetime.datetime) -> Optional[int]:
    """Gets the time delta in seconds between the time of ingestion into the system and the vaccination occurrence
    datetime. Returns None if the occurrence datetime field is not provided or is invalid."""
    occurrence_date_time = get_occurrence_datetime_from_immunisation(immunisation)

    if not occurrence_date_time:
        return None

    return math.floor((datetime_now - occurrence_date_time).total_seconds())
