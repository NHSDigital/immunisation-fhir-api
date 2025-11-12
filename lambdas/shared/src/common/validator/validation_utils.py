from datetime import date, datetime

from stdnum.verhoeff import validate


def check_if_future_date(parsed_value: date | datetime):
    """
    Ensure a parsed date or datetime object is not in the future.
    """
    if isinstance(parsed_value, datetime):
        now = datetime.now(parsed_value.tzinfo) if parsed_value.tzinfo else datetime.now()
    elif isinstance(parsed_value, date):
        now = datetime.now().date()
    if parsed_value > now:
        return True
    return False


def is_valid_simple_snomed(simple_snomed: str) -> bool:
    "check the snomed code valid or not."
    min_snomed_length = 6
    max_snomed_length = 18
    return (
        simple_snomed is not None
        and simple_snomed.isdigit()
        and simple_snomed[0] != "0"
        and min_snomed_length <= len(simple_snomed) <= max_snomed_length
        and validate(simple_snomed)
        and (simple_snomed[-3:-1] in ("00", "10"))
    )


def nhs_number_mod11_check(nhs_number: str) -> bool:
    """
    Parameters:-
    nhs_number: str
        The NHS number to be checked.
    Returns:-
        True if the nhs number passes the mod 11 check, False otherwise.

    Definition of NHS number can be found at:
    https://www.datadictionary.nhs.uk/attributes/nhs_number.html
    """
    is_mod11 = False
    if nhs_number.isdigit() and len(nhs_number) == 10:
        # Create a reversed list of weighting factors
        weighting_factors = list(range(2, 11))[::-1]
        # Multiply each of the first nine digits by the weighting factor and add the results of each multiplication
        # together
        total = sum(int(digit) * weight for digit, weight in zip(nhs_number[:-1], weighting_factors))
        # Divide the total by 11 and establish the remainder and subtract the remainder from 11 to give the check digit.
        # If the result is 11 then a check digit of 0 is used. If the result is 10 then the NHS NUMBER is invalid and
        # not used.
        check_digit = 0 if (total % 11 == 0) else (11 - (total % 11))
        # Check the remainder matches the check digit. If it does not, the NHS NUMBER is invalid.
        is_mod11 = check_digit == int(nhs_number[-1])

    return is_mod11
