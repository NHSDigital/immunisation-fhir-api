import base64
import datetime
from dataclasses import dataclass

from aws_lambda_typing.events import APIGatewayProxyEventV1
from typing import Optional
from urllib.parse import parse_qs, urlencode, quote

from clients import redis_client
from models.errors import ParameterException

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


def process_params(aws_event: APIGatewayProxyEventV1) -> ParamContainer:
    """Combines query string and content parameters. Duplicates not allowed. Splits on a comma."""

    def split_and_flatten(input: list[str]):
        return [x.strip()
                for xs in input
                for x in xs.split(",")]

    def parse_multi_value_query_parameters(
        multi_value_query_params: dict[str, list[str]]
    ) -> ParamContainer:
        if any([len(v) > 1 for k, v in multi_value_query_params.items()]):
            raise ParameterException("Parameters may not be duplicated. Use commas for \"or\".")
        params = [(k, split_and_flatten(v))
                  for k, v in multi_value_query_params.items()]

        return dict(params)

    def parse_body_params(aws_event: APIGatewayProxyEventV1) -> ParamContainer:
        http_method = aws_event.get("httpMethod")
        content_type = aws_event.get("headers", {}).get("Content-Type")
        if http_method == "POST" and content_type == "application/x-www-form-urlencoded":
            body = aws_event.get("body", "") or ""
            decoded_body = base64.b64decode(body).decode("utf-8")
            parsed_body = parse_qs(decoded_body)

            if any([len(v) > 1 for k, v in parsed_body.items()]):
                raise ParameterException("Parameters may not be duplicated. Use commas for \"or\".")
            items = dict((k, split_and_flatten(v)) for k, v in parsed_body.items())
            return items
        return {}

    query_params = parse_multi_value_query_parameters(aws_event.get("multiValueQueryStringParameters", {}) or {})
    body_params = parse_body_params(aws_event)

    if len(set(query_params.keys()) & set(body_params.keys())) > 0:
        raise ParameterException("Parameters may not be duplicated. Use commas for \"or\".")

    parsed_params = {key: sorted(query_params.get(key, []) + body_params.get(key, []))
                     for key in (query_params.keys() | body_params.keys())}

    return parsed_params


def process_search_params(params: ParamContainer) -> SearchParams:
    """Validate and parse search parameters.

    :raises ParameterException:
    """

    # patient.identifier
    patient_identifiers = params.get(patient_identifier_key, [])
    patient_identifier = patient_identifiers[0] if len(patient_identifiers) == 1 else None

    if patient_identifier is None:
        raise ParameterException(f"Search parameter {patient_identifier_key} must have one value.")

    patient_identifier_parts = patient_identifier.split("|")
    if len(patient_identifier_parts) != 2 or not patient_identifier_parts[
                                                     0] == patient_identifier_system:
        raise ParameterException("patient.identifier must be in the format of "
                      f"\"{patient_identifier_system}|{{NHS number}}\" "
                      f"e.g. \"{patient_identifier_system}|9000000009\"")

    patient_identifier = patient_identifier.split("|")[1]

    # immunization.target
    params[immunization_target_key] = list(set(params.get(immunization_target_key, [])))
    vaccine_types = [vaccine_type for vaccine_type in params[immunization_target_key] if
                     vaccine_type is not None]
    if len(vaccine_types) < 1:
        raise ParameterException(f"Search parameter {immunization_target_key} must have one or more values.")

    valid_vaccine_types = redis_client.hkeys("vacc_to_diseases")
    if any([x not in valid_vaccine_types for x in vaccine_types]):
        raise ParameterException(
            f"immunization-target must be one or more of the following: {', '.join(valid_vaccine_types)}")

    # date.from
    date_froms = params.get(date_from_key, [])

    if len(date_froms) > 1:
        raise ParameterException(f"Search parameter {date_from_key} may have one value at most.")

    try:
        date_from = datetime.datetime.strptime(date_froms[0], "%Y-%m-%d").date() \
            if len(date_froms) == 1 else date_from_default
    except ValueError:
        raise ParameterException(f"Search parameter {date_from_key} must be in format: YYYY-MM-DD")

    # date.to
    date_tos = params.get(date_to_key, [])

    if len(date_tos) > 1:
        raise ParameterException(f"Search parameter {date_to_key} may have one value at most.")

    try:
        date_to = datetime.datetime.strptime(date_tos[0], "%Y-%m-%d").date() \
            if len(date_tos) == 1 else date_to_default
    except ValueError:
        raise ParameterException(f"Search parameter {date_to_key} must be in format: YYYY-MM-DD")

    if date_from and date_to and date_from > date_to:
        raise ParameterException(f"Search parameter {date_from_key} must be before {date_to_key}")

    # include
    includes = params.get(include_key, [])
    include = includes[0] if len(includes) > 0 else None

    return SearchParams(patient_identifier, vaccine_types, date_from, date_to, include)


def create_query_string(search_params: SearchParams) -> str:
    params = [
        (immunization_target_key, ",".join(map(quote, search_params.immunization_targets))),
        (patient_identifier_key,
         f"{patient_identifier_system}|{search_params.patient_identifier}"),
        *([(date_from_key, search_params.date_from.isoformat())]
          if search_params.date_from and search_params.date_from != date_from_default else []),
        *([(date_to_key, search_params.date_to.isoformat())]
          if search_params.date_to and search_params.date_to != date_to_default else []),
        *([(include_key, search_params.include)]
          if search_params.include else []),
    ]
    search_params_qs = urlencode(sorted(params, key=lambda x: x[0]), safe=",")
    return search_params_qs
