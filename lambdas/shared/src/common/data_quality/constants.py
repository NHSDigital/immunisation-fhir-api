import datetime
import decimal

ALLOWED_DOSE_AMOUNTS = {
    # are acceptable:
    decimal.Decimal("0"),
    decimal.Decimal("0.1"),
    decimal.Decimal("0.2"),
    decimal.Decimal("0.3"),
    decimal.Decimal("0.4"),
    decimal.Decimal("0.5"),
    decimal.Decimal("0.7"),
    decimal.Decimal("1"),
    decimal.Decimal("2"),
    decimal.Decimal("10"),
    decimal.Decimal("11"),
}

ALLOWED_DOSE_UNIT_CODES = {
    # The below are all present in the existing data, but we should check which ones are acceptable:
    "258773002",  # ml
    "3317411000001100",  # dose
    "3318611000001103",  # pre-filled disposable injection
    "3319711000001103",  # unit dose
    "408102007",  # unit dose
    "413516001",  # ampoule
    "415818006",  # vial
}

MIN_ACCEPTED_PAST_DATE = datetime.date(1900, 1, 1)
MIN_ACCEPTED_EXPIRY_DATE = datetime.date(2020, 1, 1)
