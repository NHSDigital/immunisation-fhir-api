""" Convert Immunisation CSV data to Immunization Model """
import csv
from typing import Union, List

from models.csv_immunisation import CsvImmunisationModel
from models.failures import CsvImmunisationErrorModel
from pydantic import ValidationError


def generate_failed_record(row: dict, reasons: str) -> CsvImmunisationErrorModel:
    """Format an exception into a record"""
    failed_record = {
        "nhs_number": row.get("NHS_NUMBER", None),
        "unique_id": row.get("UNIQUE_ID", None),
        "failure_reasons": reasons,
    }

    immunisation_failure = CsvImmunisationErrorModel(**failed_record)

    return immunisation_failure


def read_csv_to_model(
    csv_data: str,
) -> Union[List[CsvImmunisationModel], List[CsvImmunisationErrorModel]]:
    """Read a CSV file and return a list of ImmunizationModel objects"""
    immunizations = []
    failures = []

    csv_reader = csv.DictReader(csv_data.splitlines())
    for row in csv_reader:
        try:
            # Filter out unwanted fields
            imms = CsvImmunisationModel(**row)
            immunizations.append(imms)
        except ValidationError as failure:
            # ValidationError's errors() method returns a list of errors
            reasons = failure.errors()
            immunisation_failure = generate_failed_record(row, reasons)
            failures.append(immunisation_failure)

        except ValueError as failure:
            # ValueError just returns a string for the error so we'll add it to a list
            reasons = [str(failure)]
            immunisation_failure = generate_failed_record(row, reasons)
            failures.append(immunisation_failure)

        except Exception as failure:
            # A catch all for anything else that might go wrong
            reasons = [str(failure)]
            immunisation_failure = generate_failed_record(row, reasons)
            failures.append(immunisation_failure)

    return immunizations, failures
