"""Simple immunization model to support data quality validation. The team only requires simple validation on a subset
of the immunization fields"""

import datetime
import decimal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, condate, constr, validator

from common.data_quality.constants import (
    ALLOWED_DOSE_AMOUNTS,
    ALLOWED_DOSE_UNIT_CODES,
    MIN_ACCEPTED_EXPIRY_DATE,
    MIN_ACCEPTED_PAST_DATE,
)
from common.data_quality.timeliness import parse_csv_date, parse_csv_datetime

# Consider upgrading fhir.resources 7 -> 8 and pydantic 1 -> 2 to use the more powerful and readable Annotated types
# and constraints
NhsNumber = constr(min_length=10, max_length=10, regex=r"^\d{10}$")
BatchCsvDate = condate(ge=MIN_ACCEPTED_PAST_DATE)
PersonPostcode = constr(regex=r"^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$")
ExpiryDate = condate(ge=MIN_ACCEPTED_EXPIRY_DATE)
SnomedCode = constr(min_length=6, max_length=18, regex=r"^\d{6,18}$")


class ImmunizationBatchRowModel(BaseModel):
    """Represents the Immunization as provided in batch CSV. Contains the subset of fields for DQ validation."""

    NHS_NUMBER: NhsNumber
    PERSON_DOB: BatchCsvDate
    DATE_AND_TIME: BatchCsvDate
    PERSON_POSTCODE: PersonPostcode
    EXPIRY_DATE: ExpiryDate  # TODO - check with DQ team. Should these checks be relative to the occurrence datetime?
    DOSE_AMOUNT: decimal.Decimal  # TODO - check with DQ team. Actual values vary a lot from proposed enum.
    SITE_OF_VACCINATION_CODE: SnomedCode  # TODO - check with DQ team. Their reqs are quite rudimentary, could change?
    ROUTE_OF_VACCINATION_CODE: SnomedCode
    DOSE_UNIT_CODE: str  # TODO - check with DQ team. Their enum does not match up with what this data actually is.
    INDICATION_CODE: SnomedCode

    @validator("PERSON_DOB", "EXPIRY_DATE", pre=True)
    def parse_csv_date(cls, value: str) -> datetime.date:
        return parse_csv_date(value)

    @validator("PERSON_DOB", "DATE_AND_TIME")
    def ensure_past_date(cls, value: datetime.date) -> datetime.date:
        if value >= datetime.date.today():
            raise ValueError("Date must be in the past")

        return value

    @validator("DATE_AND_TIME", pre=True)
    def parse_csv_datetime(cls, value: str) -> datetime.datetime:
        return parse_csv_datetime(value)

    @validator("EXPIRY_DATE")
    def is_expiry_within_a_year(cls, value: datetime.date) -> datetime.date:
        if value > datetime.date.today() + relativedelta(years=1):
            raise ValueError("EXPIRY_DATE must be within a year from today")

        return value

    @validator("DOSE_AMOUNT")
    def is_valid_dose_amount(cls, value: decimal.Decimal) -> decimal.Decimal:
        if value not in ALLOWED_DOSE_AMOUNTS:
            raise ValueError("Invalid DOSE_AMOUNT provided")

        return value

    @validator("DOSE_UNIT_CODE")
    def is_valid_dose_unit_code(cls, value: str) -> str:
        if value not in ALLOWED_DOSE_UNIT_CODES:
            raise ValueError("Invalid DOSE_UNIT_CODE provided")

        return value
