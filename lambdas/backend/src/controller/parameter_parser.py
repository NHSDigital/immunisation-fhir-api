import datetime
from dataclasses import dataclass
from typing import Optional

from common.models.constants import Constants
from common.models.utils.generic_utils import nhs_number_mod11_check
from common.redis_client import get_redis_client
from controller.constants import IdentifierSearchElement, IdentifierSearchParameterName, ImmunizationSearchParameterName
from models.errors import ParameterExceptionError

DUPLICATED_PARAMETERS_ERROR_MESSAGE = 'Parameters may not be duplicated. Use commas for "or".'
INVALID_IDENTIFIER_ERROR_MESSAGE = (
    'Search parameter identifier must have one value and must be in the format of "iden'
    'tifier.system|identifier.value" "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
)
NO_PARAMETERS_ERROR_MESSAGE = "No parameter provided. Search using either identifier or patient.identifier."

PATIENT_IDENTIFIER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"


@dataclass
class SearchParams:
    patient_identifier: str
    immunization_targets: set[str]
    date_from: Optional[datetime.date]
    date_to: Optional[datetime.date]
    include: Optional[str]

    def __repr__(self):
        return str(self.__dict__)


def process_patient_identifier(identifier_params: dict[str, list[str]]) -> str:
    """Validate and parse patient identifier parameter.

    :raises ParameterExceptionError:
    """
    patient_identifiers = identifier_params.get(ImmunizationSearchParameterName.PATIENT_IDENTIFIER, [])

    if len(patient_identifiers) != 1:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.PATIENT_IDENTIFIER} must have one value."
        )

    patient_identifier_parts = patient_identifiers[0].split("|")
    identifier_system = patient_identifier_parts[0]

    if len(patient_identifier_parts) != 2 or identifier_system != PATIENT_IDENTIFIER_SYSTEM:
        raise ParameterExceptionError(
            "patient.identifier must be in the format of "
            f'"{PATIENT_IDENTIFIER_SYSTEM}|{{NHS number}}" '
            f'e.g. "{PATIENT_IDENTIFIER_SYSTEM}|9000000009"'
        )

    nhs_number = patient_identifier_parts[1]

    if not nhs_number_mod11_check(nhs_number):
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.PATIENT_IDENTIFIER} must be a valid NHS number."
        )

    return nhs_number


def process_immunization_target(imms_params: dict[str, list[str]]) -> set[str]:
    """Validate and parse immunization target parameter.

    :raises ParameterExceptionError:
    """
    vaccine_types = [
        vaccine_type
        for vaccine_type in set(imms_params.get(ImmunizationSearchParameterName.IMMUNIZATION_TARGET, []))
        if vaccine_type is not None
    ]

    if len(vaccine_types) < 1:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.IMMUNIZATION_TARGET} must have one or more values."
        )

    valid_vaccine_types = get_redis_client().hkeys(Constants.VACCINE_TYPE_TO_DISEASES_HASH_KEY)
    if any(x not in valid_vaccine_types for x in vaccine_types):
        raise ParameterExceptionError(
            f"{ImmunizationSearchParameterName.IMMUNIZATION_TARGET} must be one or more of the following: "
            f"{', '.join(valid_vaccine_types)}"
        )

    return set(vaccine_types)


def process_mandatory_params(params: dict[str, list[str]]) -> tuple[str, set[str]]:
    """Validate mandatory params and return (patient_identifier, vaccine_types).
    Raises ParameterExceptionError for any validation error.
    """
    patient_identifier = process_patient_identifier(params)
    vaccine_types = process_immunization_target(params)

    return patient_identifier, vaccine_types


def process_optional_params(
    params: dict[str, list[str]],
) -> tuple[Optional[datetime.date], Optional[datetime.date], Optional[str]]:
    """Parse optional params (date.from, date.to, _include).
    Raises ParameterExceptionError for any validation error.
    """
    include = None
    date_from = None
    date_to = None

    date_froms = params.get(ImmunizationSearchParameterName.DATE_FROM, [])
    date_tos = params.get(ImmunizationSearchParameterName.DATE_TO, [])
    includes = params.get(ImmunizationSearchParameterName.INCLUDE, [])

    if date_froms:
        if len(date_froms) != 1:
            raise ParameterExceptionError(
                f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} may have one value at most."
            )
        try:
            date_from = datetime.datetime.strptime(date_froms[0], "%Y-%m-%d").date()
        except ValueError:
            raise ParameterExceptionError(
                f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} must be in format: YYYY-MM-DD"
            )

    if date_tos:
        if len(date_tos) != 1:
            raise ParameterExceptionError(
                f"Search parameter {ImmunizationSearchParameterName.DATE_TO} may have one value at most."
            )
        try:
            date_to = datetime.datetime.strptime(date_tos[0], "%Y-%m-%d").date()
        except ValueError:
            raise ParameterExceptionError(
                f"Search parameter {ImmunizationSearchParameterName.DATE_TO} must be in format: YYYY-MM-DD"
            )

    if includes:
        if includes[0].lower() != "immunization:patient":
            raise ParameterExceptionError(
                f"Search parameter {ImmunizationSearchParameterName.INCLUDE} may only be "
                f"'Immunization:patient' if provided."
            )
        include = includes[0]

    return date_from, date_to, include


def validate_and_retrieve_search_params(params: dict[str, list[str]]) -> SearchParams:
    """Validate and retrieve search parameters.
    :raises ParameterExceptionError:
    """
    patient_identifier, vaccine_types = process_mandatory_params(params)
    date_from, date_to, include = process_optional_params(params)

    if date_from and date_to and date_from > date_to:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} must be before "
            f"{ImmunizationSearchParameterName.DATE_TO}"
        )

    return SearchParams(patient_identifier, vaccine_types, date_from, date_to, include)


def parse_search_params(search_params_in_req: dict[str, list[str]]) -> dict[str, list[str]]:
    """Ensures the search params provided in the event do not contain duplicated keys. Will split the parameters
    provided by comma separators. Raises a ParameterExceptionError for duplicated keys. Existing business logic stipulated
    that the API only accepts comma separated values rather than multi-value."""
    if any([len(values) > 1 for _, values in search_params_in_req.items()]):
        raise ParameterExceptionError(DUPLICATED_PARAMETERS_ERROR_MESSAGE)

    parsed_params = {}

    for key, param_values in search_params_in_req.items():
        if len(param_values) == 0:
            parsed_params[key] = []
            continue

        parsed_params[key] = [param.strip() for param_str in param_values for param in param_str.split(",")]

    if len(parsed_params) == 0:
        raise ParameterExceptionError(message=NO_PARAMETERS_ERROR_MESSAGE)

    return parsed_params


def check_identifier_search_params_contain_no_incorrect_keys(search_params: dict[str, list[str]]) -> bool:
    for patient_vacc_type_search_param in ImmunizationSearchParameterName:
        if patient_vacc_type_search_param in search_params:
            return False

    return True


def check_elements_valid(elements: list[str]) -> bool:
    return set(elements).issubset({IdentifierSearchElement.ID, IdentifierSearchElement.META})


def validate_and_retrieve_identifier_search_params(params: dict[str, list[str]]) -> tuple[str, Optional[set[str]]]:
    contains_no_patient_vacc_type_params = check_identifier_search_params_contain_no_incorrect_keys(params)

    if not contains_no_patient_vacc_type_params:
        if (
            ImmunizationSearchParameterName.PATIENT_IDENTIFIER in params
            and IdentifierSearchParameterName.IDENTIFIER in params
        ):
            raise ParameterExceptionError("Search parameter should have either identifier or patient.identifier")

        raise ParameterExceptionError("Identifier search included patient.identifier search parameters")

    # Would we want to permit searching with multiple identifiers in future?
    identifiers_list = params.get(IdentifierSearchParameterName.IDENTIFIER, [])

    if len(identifiers_list) > 1:
        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    identifier = identifiers_list[0] if identifiers_list else None
    elements = params.get(IdentifierSearchParameterName.ELEMENTS)

    if not identifier:
        if elements is not None:
            raise ParameterExceptionError("Search parameter _elements must have the following parameter: identifier")

        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    if "|" not in identifier or " " in identifier:
        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    if not elements:
        return identifier, None

    if not check_elements_valid(elements):
        raise ParameterExceptionError("_elements must be one or more of the following: id,meta")

    return identifier, set(elements)
