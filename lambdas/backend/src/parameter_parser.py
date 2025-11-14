import base64
import datetime
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, quote, urlencode

from aws_lambda_typing.events import APIGatewayProxyEventV1

from common.models.constants import Constants
from common.models.utils.generic_utils import nhs_number_mod11_check
from common.redis_client import get_redis_client
from models.errors import ParameterException

ERROR_MESSAGE_DUPLICATED_PARAMETERS = 'Parameters may not be duplicated. Use commas for "or".'

ParamValue = list[str]
ParamContainer = dict[str, ParamValue]

patient_identifier_system = "https://fhir.nhs.uk/Id/nhs-number"

patient_identifier_key = "patient.identifier"
immunization_target_key = "-immunization.target"
date_from_key = "-date.from"
date_from_default = datetime.date(1900, 1, 1)
date_to_key = "-date.to"
date_to_default = datetime.date(9999, 12, 31)
include_key = "_include"


@dataclass
class SearchParams:
    patient_identifier: str
    immunization_targets: list[str]
    date_from: Optional[datetime.date]
    date_to: Optional[datetime.date]
    include: Optional[str]

    def __repr__(self):
        return str(self.__dict__)


def process_patient_identifier(identifier_params: ParamContainer) -> str:
    """Validate and parse patient identifier parameter.

    :raises ParameterException:
    """
    patient_identifiers = identifier_params.get(patient_identifier_key, [])
    patient_identifier = patient_identifiers[0] if len(patient_identifiers) == 1 else None

    if patient_identifier is None:
        raise ParameterException(f"Search parameter {patient_identifier_key} must have one value.")

    patient_identifier_parts = patient_identifier.split("|")
    identifier_system = patient_identifier_parts[0]
    if len(patient_identifier_parts) != 2 or identifier_system != patient_identifier_system:
        raise ParameterException(
            "patient.identifier must be in the format of "
            f'"{patient_identifier_system}|{{NHS number}}" '
            f'e.g. "{patient_identifier_system}|9000000009"'
        )

    nhs_number = patient_identifier_parts[1]
    if not nhs_number_mod11_check(nhs_number):
        raise ParameterException("Search parameter patient.identifier must be a valid NHS number.")

    return nhs_number


def process_immunization_target(imms_params: ParamContainer) -> list[str]:
    """Validate and parse immunization target parameter.

    :raises ParameterException:
    """
    vaccine_types = [
        vaccine_type for vaccine_type in set(imms_params.get(immunization_target_key, [])) if vaccine_type is not None
    ]
    if len(vaccine_types) < 1:
        raise ParameterException(f"Search parameter {immunization_target_key} must have one or more values.")

    valid_vaccine_types = get_redis_client().hkeys(Constants.VACCINE_TYPE_TO_DISEASES_HASH_KEY)
    if any(x not in valid_vaccine_types for x in vaccine_types):
        raise ParameterException(
            f"immunization-target must be one or more of the following: {', '.join(valid_vaccine_types)}"
        )

    return vaccine_types


def process_mandatory_params(params: ParamContainer) -> tuple[str, list[str]]:
    """Validate mandatory params and return (patient_identifier, vaccine_types).
    Raises ParameterException for any validation error.
    """
    # patient.identifier
    patient_identifier = process_patient_identifier(params)

    # immunization.target
    vaccine_types = process_immunization_target(params)

    return patient_identifier, vaccine_types


def process_optional_params(
    params: ParamContainer,
) -> tuple[datetime.date, datetime.date, Optional[str], list[str]]:
    """Parse optional params (date.from, date.to, _include).
    Returns (date_from, date_to, include, errors).
    """
    errors: list[str] = []
    date_from = None
    date_to = None

    date_froms = params.get(date_from_key, [])
    if len(date_froms) > 1:
        errors.append(f"Search parameter {date_from_key} may have one value at most.")

    try:
        date_from = (
            datetime.datetime.strptime(date_froms[0], "%Y-%m-%d").date() if len(date_froms) == 1 else date_from_default
        )
    except ValueError:
        errors.append(f"Search parameter {date_from_key} must be in format: YYYY-MM-DD")

    date_tos = params.get(date_to_key, [])
    if len(date_tos) > 1:
        errors.append(f"Search parameter {date_to_key} may have one value at most.")

    try:
        date_to = datetime.datetime.strptime(date_tos[0], "%Y-%m-%d").date() if len(date_tos) == 1 else date_to_default
    except ValueError:
        errors.append(f"Search parameter {date_to_key} must be in format: YYYY-MM-DD")

    includes = params.get(include_key, [])
    if includes and includes[0].lower() != "immunization:patient":
        errors.append(f"Search parameter {include_key} may only be 'Immunization:patient' if provided.")
    include = includes[0] if len(includes) > 0 else None

    return date_from, date_to, include, errors


def process_search_params(params: ParamContainer) -> SearchParams:
    """Validate and parse search parameters.
    :raises ParameterException:
    """
    patient_identifier, vaccine_types = process_mandatory_params(params)
    date_from, date_to, include, errors = process_optional_params(params)

    if date_from and date_to and date_from > date_to:
        errors.append(f"Search parameter {date_from_key} must be before {date_to_key}")

    if errors:
        raise ParameterException("; ".join(errors))

    return SearchParams(patient_identifier, vaccine_types, date_from, date_to, include)


def process_params(aws_event: APIGatewayProxyEventV1) -> ParamContainer:
    """Combines query string and content parameters. Duplicates not allowed. Splits on a comma."""

    def split_and_flatten(input: list[str]):
        return [x.strip() for xs in input for x in xs.split(",")]

    def parse_multi_value_query_parameters(
        multi_value_query_params: dict[str, list[str]],
    ) -> ParamContainer:
        if any(len(v) > 1 for k, v in multi_value_query_params.items()):
            raise ParameterException(ERROR_MESSAGE_DUPLICATED_PARAMETERS)
        params = [(k, split_and_flatten(v)) for k, v in multi_value_query_params.items()]

        return dict(params)

    def parse_body_params(aws_event: APIGatewayProxyEventV1) -> ParamContainer:
        http_method = aws_event.get("httpMethod")
        content_type = aws_event.get("headers", {}).get("Content-Type")
        if http_method == "POST" and content_type == "application/x-www-form-urlencoded":
            body = aws_event.get("body", "") or ""
            decoded_body = base64.b64decode(body).decode("utf-8")
            parsed_body = parse_qs(decoded_body)

            if any(len(v) > 1 for k, v in parsed_body.items()):
                raise ParameterException(ERROR_MESSAGE_DUPLICATED_PARAMETERS)
            items = {k: split_and_flatten(v) for k, v in parsed_body.items()}
            return items
        return {}

    query_params = parse_multi_value_query_parameters(aws_event.get("multiValueQueryStringParameters", {}) or {})
    body_params = parse_body_params(aws_event)

    if len(set(query_params.keys()) & set(body_params.keys())) > 0:
        raise ParameterException(ERROR_MESSAGE_DUPLICATED_PARAMETERS)

    parsed_params = {
        key: sorted(query_params.get(key, []) + body_params.get(key, []))
        for key in (query_params.keys() | body_params.keys())
    }

    return parsed_params


def create_query_string(search_params: SearchParams) -> str:
    params = [
        (
            immunization_target_key,
            ",".join(map(quote, search_params.immunization_targets)),
        ),
        (
            patient_identifier_key,
            f"{patient_identifier_system}|{search_params.patient_identifier}",
        ),
        *(
            [(date_from_key, search_params.date_from.isoformat())]
            if search_params.date_from and search_params.date_from != date_from_default
            else []
        ),
        *(
            [(date_to_key, search_params.date_to.isoformat())]
            if search_params.date_to and search_params.date_to != date_to_default
            else []
        ),
        *([(include_key, search_params.include)] if search_params.include else []),
    ]
    search_params_qs = urlencode(sorted(params, key=lambda x: x[0]), safe=",")
    return search_params_qs
