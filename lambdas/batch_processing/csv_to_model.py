import csv
from models.immunization import ImmunizationModel
import datetime


def parse_iso8601_datetime(iso_datetime_str):
    try:
        # Parse ISO 8601 datetime string with timezone offset
        dt = datetime.fromisoformat(iso_datetime_str)

        # Convert the parsed datetime to the system's local timezone
        dt = dt.astimezone()

        return dt
    except ValueError:
        return None


# Define a function to read and transform the CSV file
def read_csv_to_immunizations(csv_data):
    immunizations = [] = []

    csv_reader = csv.DictReader(csv_data.splitlines())
    for row in csv_reader:
        # Parse datetime fields if needed
        if row["PERSON_DOB"]:
            row["PERSON_DOB"] = datetime.strptime(row["PERSON_DOB"], "%Y-%m-%d").date()
        if row["DATE_AND_TIME"]:
            row["DATE_AND_TIME"] = parse_iso8601_datetime(row["DATE_AND_TIME"])
        if row["RECORDED_DATE"]:
            row["RECORDED_DATE"] = datetime.strptime(
                row["RECORDED_DATE"], "%Y-%m-%d"
            ).date()
        if row["EXPIRY_DATE"]:
            row["EXPIRY_DATE"] = datetime.strptime(
                row["EXPIRY_DATE"], "%Y-%m-%d"
            ).date()
        immunization = ImmunizationModel(**row)
        if immunization is not None:
            immunizations.append(immunization)

    return immunizations
