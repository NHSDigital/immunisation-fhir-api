import base64
import json
import os
import re
from decimal import Decimal
from json import JSONDecodeError
from urllib.parse import parse_qs

from aws_lambda_typing.events import APIGatewayProxyEventV1
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.identifier import Identifier

from constants import MAX_RESPONSE_SIZE_BYTES
from controller.aws_apig_event_utils import (
    get_multi_value_query_params,
    get_path_parameter,
    get_resource_version_header,
    get_supplier_system_header,
)
from controller.aws_apig_response_utils import create_response
from controller.constants import E_TAG_HEADER_NAME, IdentifierSearchParameterName
from controller.fhir_api_exception_handler import fhir_api_exception_handler
from controller.parameter_parser import (
    parse_search_params,
    validate_and_retrieve_identifier_search_params,
    validate_and_retrieve_search_params,
)
from models.errors import (
    InconsistentIdError,
    InvalidImmunizationIdError,
    InvalidJsonError,
    InvalidResourceVersionError,
    TooManyResultsError,
)
from repository.fhir_repository import ImmunizationRepository, create_table
from service.fhir_service import FhirService, get_service_url

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")


def make_controller(
    immunization_env: str = IMMUNIZATION_ENV,
):
    endpoint_url = "http://localhost:4566" if immunization_env == "local" else None
    imms_repo = ImmunizationRepository(create_table(endpoint_url=endpoint_url))

    service = FhirService(imms_repo=imms_repo)

    return FhirController(fhir_service=service)


class FhirController:
    _IMMUNIZATION_ID_PATTERN = r"^[A-Za-z0-9\-.]{1,64}$"
    _API_SERVICE_URL = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)

    def __init__(
        self,
        fhir_service: FhirService,
    ):
        self.fhir_service = fhir_service

    @fhir_api_exception_handler
    def get_immunization_by_id(self, aws_event: APIGatewayProxyEventV1) -> dict:
        imms_id = get_path_parameter(aws_event, "id")

        if not self._is_valid_immunization_id(imms_id):
            raise InvalidImmunizationIdError()

        supplier_system = get_supplier_system_header(aws_event)

        resource, version = self.fhir_service.get_immunization_and_version_by_id(imms_id, supplier_system)

        return create_response(200, resource.json(), {E_TAG_HEADER_NAME: version})

    @fhir_api_exception_handler
    def create_immunization(self, aws_event: APIGatewayProxyEventV1) -> dict:
        supplier_system = get_supplier_system_header(aws_event)

        try:
            immunisation: dict = json.loads(aws_event["body"], parse_float=Decimal)
        except JSONDecodeError as e:
            raise InvalidJsonError(message=str(f"Request's body contains malformed JSON: {e}"))

        created_resource_id = self.fhir_service.create_immunization(immunisation, supplier_system)

        return create_response(
            status_code=201,
            body=None,
            headers={"Location": f"{self._API_SERVICE_URL}/Immunization/{created_resource_id}", "E-Tag": "1"},
        )

    @fhir_api_exception_handler
    def update_immunization(self, aws_event: APIGatewayProxyEventV1) -> dict:
        imms_id = get_path_parameter(aws_event, "id")
        supplier_system = get_supplier_system_header(aws_event)
        resource_version = get_resource_version_header(aws_event)

        if not self._is_valid_immunization_id(imms_id):
            raise InvalidImmunizationIdError()

        if not self._is_valid_resource_version(resource_version):
            raise InvalidResourceVersionError(resource_version=resource_version)

        try:
            immunization = json.loads(aws_event["body"], parse_float=Decimal)
        except JSONDecodeError as e:
            # Consider moving the start of the message into a const
            raise InvalidJsonError(message=str(f"Request's body contains malformed JSON: {e}"))

        if immunization.get("id") != imms_id:
            raise InconsistentIdError(imms_id=imms_id)

        updated_resource_version = self.fhir_service.update_immunization(
            imms_id, immunization, supplier_system, int(resource_version)
        )
        return create_response(200, None, {E_TAG_HEADER_NAME: updated_resource_version})

    @fhir_api_exception_handler
    def delete_immunization(self, aws_event: APIGatewayProxyEventV1) -> dict:
        imms_id = get_path_parameter(aws_event, "id")

        if not self._is_valid_immunization_id(imms_id):
            raise InvalidImmunizationIdError()

        supplier_system = get_supplier_system_header(aws_event)

        self.fhir_service.delete_immunization(imms_id, supplier_system)

        return create_response(204)

    @fhir_api_exception_handler
    def search_immunizations(self, aws_event: APIGatewayProxyEventV1, is_post_endpoint_req: bool = False) -> dict:
        """Performs the client search request based on the parameters provided. The available searches are:
        1. Search by identifier: (more like a GET) retrieves immunisation by local identifier.
        2. Search by patient and immunisation target"""
        search_params = self._get_search_params_from_request(aws_event, is_post_endpoint_req)
        parsed_search_params = parse_search_params(search_params)
        supplier_system = get_supplier_system_header(aws_event)

        if self._is_identifier_search(parsed_search_params):
            return self._get_immunization_by_identifier(parsed_search_params, supplier_system)

        return self._search_immunizations(parsed_search_params, supplier_system)

    def _get_immunization_by_identifier(self, search_params: dict[str, list[str]], supplier_system: str) -> dict:
        raw_identifier, element = validate_and_retrieve_identifier_search_params(search_params)
        identifier_components = raw_identifier.split("|", 1)
        identifier = Identifier.construct(system=identifier_components[0], value=identifier_components[1])

        search_bundle = self.fhir_service.get_immunization_by_identifier(identifier, supplier_system, element)
        prepared_search_bundle = self._prepare_search_bundle(search_bundle)

        return create_response(200, prepared_search_bundle)

    def _search_immunizations(self, search_params: dict[str, list[str]], supplier_system: str) -> dict:
        validated_search_params = validate_and_retrieve_search_params(search_params)

        search_bundle = self.fhir_service.search_immunizations(
            validated_search_params.patient_identifier,
            validated_search_params.IMMUNIZATION_TARGETS,
            supplier_system,
            validated_search_params.date_from,
            validated_search_params.date_to,
            validated_search_params.include,
        )

        if self._has_too_many_search_results(search_bundle):
            raise TooManyResultsError("Search returned too many results. Please narrow down the search")

        prepared_search_bundle = self._prepare_search_bundle(search_bundle)

        return create_response(200, prepared_search_bundle)

    def _is_valid_immunization_id(self, immunization_id: str) -> bool:
        """Validates if the given unique Immunization ID is valid."""
        return False if not re.match(self._IMMUNIZATION_ID_PATTERN, immunization_id) else True

    @staticmethod
    def _prepare_search_bundle(search_response: Bundle) -> dict:
        """Workaround for fhir.resources dict() or json() removing the empty "entry" list. Team also specified that
        total should be the final key in the object. Should investigate if this can be resolved with later version of
        the library."""
        search_response_dict = json.loads(search_response.json())

        if "entry" not in search_response_dict:
            search_response_dict["entry"] = []

        search_response_dict["total"] = search_response_dict.pop("total")
        return search_response_dict

    @staticmethod
    def _is_valid_resource_version(resource_version: str) -> bool:
        return resource_version.isdigit() and int(resource_version) > 0

    @staticmethod
    def _is_identifier_search(search_params: dict[str, list[str]]) -> bool:
        """Checks whether a given search is an identifier or patient + vacc type search based on the parameters"""
        return (
            IdentifierSearchParameterName.IDENTIFIER in search_params
            or IdentifierSearchParameterName.ELEMENTS in search_params
        )

    @staticmethod
    def _has_too_many_search_results(search_response: Bundle) -> bool:
        """Checks whether the response is too large - 6MB Lambda limit. Note: this condition should never happen as it
        would require a very large number of vaccs for a single patient. It is also very rudimentary and all it does is
        ensure we can raise and return a nice looking error. Consider using pagination as a more robust approach."""
        return len(search_response.json(use_decimal=True)) > MAX_RESPONSE_SIZE_BYTES

    @staticmethod
    def _get_search_params_from_request(
        aws_event: APIGatewayProxyEventV1, is_post_endpoint_req: bool
    ) -> dict[str, list[str]]:
        """Simple helper function to retrieve the search params from the relevant part of the AWS event, depending on
        which search endpoint is being used"""
        if not is_post_endpoint_req:
            multi_value_params = get_multi_value_query_params(aws_event)
            return multi_value_params if multi_value_params is not None else {}

        form_body = aws_event.get("body")

        if not form_body:
            return {}

        decoded_body = base64.b64decode(form_body).decode("utf-8")
        return parse_qs(decoded_body)
