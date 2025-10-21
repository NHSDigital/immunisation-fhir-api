import base64
import json
import os
import re
import urllib.parse
import uuid
from decimal import Decimal
from json import JSONDecodeError
from typing import Optional

from aws_lambda_typing.events import APIGatewayProxyEventV1

from controller.aws_apig_event_utils import (
    get_path_parameter,
    get_supplier_system_header,
)
from controller.aws_apig_response_utils import create_response
from controller.constants import E_TAG_HEADER_NAME
from controller.fhir_api_exception_handler import fhir_api_exception_handler
from models.errors import (
    Code,
    IdentifierDuplicationError,
    InvalidImmunizationId,
    InvalidJsonError,
    ParameterException,
    Severity,
    UnauthorizedError,
    UnauthorizedVaxError,
    UnhandledResponseError,
    ValidationError,
    create_operation_outcome,
)
from models.utils.generic_utils import check_keys_in_sources
from parameter_parser import create_query_string, process_params, process_search_params
from repository.fhir_repository import ImmunizationRepository, create_table
from service.fhir_service import FhirService, UpdateOutcome, get_service_url

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")


def make_controller(
    immunization_env: str = IMMUNIZATION_ENV,
):
    endpoint_url = "http://localhost:4566" if immunization_env == "local" else None
    imms_repo = ImmunizationRepository(create_table(endpoint_url=endpoint_url))

    service = FhirService(imms_repo=imms_repo)

    return FhirController(fhir_service=service)


class FhirController:
    _IMMUNIZATION_ID_PATTERN = r"^[A-Za-z0-9\-.]{1,64}$"
    _API_SERVICE_URL = get_service_url()

    def __init__(
        self,
        fhir_service: FhirService,
    ):
        self.fhir_service = fhir_service

    def get_immunization_by_identifier(self, aws_event) -> dict:
        try:
            if aws_event.get("headers"):
                query_params = aws_event.get("queryStringParameters", {})
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())
        body = aws_event["body"]
        if query_params and body:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=('Parameters may not be duplicated. Use commas for "or".'),
            )
            return create_response(400, error)
        identifier, element, not_required, has_imms_identifier, has_element = self.fetch_identifier_system_and_element(
            aws_event
        )
        if not_required:
            return self.create_response_for_identifier(not_required, has_imms_identifier, has_element)
        # If not found, retrieve from multiValueQueryStringParameters
        if id_error := self._validate_identifier_system(identifier, element):
            return create_response(400, id_error)
        identifiers = identifier.replace("|", "#")
        supplier_system = self._identify_supplier_system(aws_event)

        try:
            if resource := self.fhir_service.get_immunization_by_identifier(
                identifiers, supplier_system, identifier, element
            ):
                return create_response(200, resource)
        except UnauthorizedVaxError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())

    @fhir_api_exception_handler
    def get_immunization_by_id(self, aws_event: APIGatewayProxyEventV1) -> dict:
        imms_id = get_path_parameter(aws_event, "id")

        if not self._is_valid_immunization_id(imms_id):
            raise InvalidImmunizationId()

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

    def update_immunization(self, aws_event):
        try:
            if aws_event.get("headers"):
                imms_id = aws_event["pathParameters"]["id"]
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())

        supplier_system = self._identify_supplier_system(aws_event)

        # Refactor to raise InvalidImmunizationId when working on VED-747
        if not self._is_valid_immunization_id(imms_id):
            return create_response(
                400,
                json.dumps(
                    create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invalid,
                        diagnostics="Validation errors: the provided event ID is either missing or not in the expected "
                        "format.",
                    )
                ),
            )

        # Validate the body of the request - start
        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
            # Validate the imms id in the path params and body of request - start
            if imms.get("id") != imms_id:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=(
                        f"Validation errors: The provided immunization id:{imms_id} doesn't match with the content of "
                        "the request body"
                    ),
                )
                return create_response(400, json.dumps(exp_error))
            # Validate the imms id in the path params and body of request - end
        except JSONDecodeError as e:
            return self._create_bad_request(f"Request's body contains malformed JSON: {e}")
        except Exception as e:
            return self._create_bad_request(f"Request's body contains string: {e}")
        # Validate the body of the request - end

        # Validate if the imms resource does not exist - start
        try:
            existing_record = self.fhir_service.get_immunization_by_id_all(imms_id, imms)
            if not existing_record:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.not_found,
                    diagnostics=(
                        f"Validation errors: The requested immunization resource with id:{imms_id} was not found."
                    ),
                )
                return create_response(404, json.dumps(exp_error))

            if "diagnostics" in existing_record:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=existing_record["diagnostics"],
                )
                return create_response(400, json.dumps(exp_error))
        except ValidationError as error:
            return create_response(400, error.to_operation_outcome())
        # Validate if the imms resource does not exist - end

        existing_resource_version = int(existing_record["Version"])
        existing_resource_vacc_type = existing_record["VaccineType"]

        try:
            # Validate if the imms resource to be updated is a logically deleted resource - start
            if existing_record["DeletedAt"]:
                outcome, resource, updated_version = self.fhir_service.reinstate_immunization(
                    imms_id,
                    imms,
                    existing_resource_version,
                    existing_resource_vacc_type,
                    supplier_system,
                )
            # Validate if the imms resource to be updated is a logically deleted resource-end
            else:
                # Validate if imms resource version is part of the request - start
                if "E-Tag" not in aws_event["headers"]:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=(
                            "Validation errors: Immunization resource version not specified in the request headers"
                        ),
                    )
                    return create_response(400, json.dumps(exp_error))
                # Validate if imms resource version is part of the request - end

                # Validate the imms resource version provided in the request headers - start
                try:
                    resource_version_header = int(aws_event["headers"]["E-Tag"])
                except (TypeError, ValueError):
                    resource_version = aws_event["headers"]["E-Tag"]
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=(
                            f"Validation errors: Immunization resource version:{resource_version} in the request "
                            "headers is invalid."
                        ),
                    )
                    return create_response(400, json.dumps(exp_error))
                # Validate the imms resource version provided in the request headers - end

                # Validate if resource version has changed since the last retrieve - start
                if existing_resource_version > resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=(
                            f"Validation errors: The requested immunization resource {imms_id} has changed since the "
                            "last retrieve."
                        ),
                    )
                    return create_response(400, json.dumps(exp_error))
                if existing_resource_version < resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=(
                            f"Validation errors: The requested immunization resource {imms_id} version is inconsistent "
                            "with the existing version."
                        ),
                    )
                    return create_response(400, json.dumps(exp_error))
                # Validate if resource version has changed since the last retrieve - end

                # Check if the record is reinstated record - start
                if existing_record["Reinstated"] is True:
                    outcome, resource, updated_version = self.fhir_service.update_reinstated_immunization(
                        imms_id,
                        imms,
                        existing_resource_version,
                        existing_resource_vacc_type,
                        supplier_system,
                    )
                else:
                    outcome, resource, updated_version = self.fhir_service.update_immunization(
                        imms_id,
                        imms,
                        existing_resource_version,
                        existing_resource_vacc_type,
                        supplier_system,
                    )

                # Check if the record is reinstated record - end

            # Check for errors returned on update
            if "diagnostics" in resource:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=resource["diagnostics"],
                )
                return create_response(400, json.dumps(exp_error))
            if outcome == UpdateOutcome.UPDATE:
                return create_response(
                    200, None, {"E-Tag": updated_version}
                )  # include e-tag here, is it not included in the response resource
        except ValidationError as error:
            return create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as duplicate:
            return create_response(422, duplicate.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())

    @fhir_api_exception_handler
    def delete_immunization(self, aws_event: APIGatewayProxyEventV1) -> dict:
        imms_id = get_path_parameter(aws_event, "id")

        if not self._is_valid_immunization_id(imms_id):
            raise InvalidImmunizationId()

        supplier_system = get_supplier_system_header(aws_event)

        self.fhir_service.delete_immunization(imms_id, supplier_system)

        return create_response(204)

    def search_immunizations(self, aws_event: APIGatewayProxyEventV1) -> dict:
        try:
            search_params = process_search_params(process_params(aws_event))
        except ParameterException as e:
            return self._create_bad_request(e.message)
        if search_params is None:
            raise Exception("Failed to parse parameters.")

        # Check vaxx type permissions- start
        try:
            if aws_event.get("headers"):
                supplier_system = self._identify_supplier_system(aws_event)
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())

        try:
            result, request_contained_unauthorised_vaccs = self.fhir_service.search_immunizations(
                search_params.patient_identifier,
                search_params.immunization_targets,
                create_query_string(search_params),
                supplier_system,
                search_params.date_from,
                search_params.date_to,
            )
        except UnauthorizedVaxError as unauthorized:
            return create_response(403, unauthorized.to_operation_outcome())

        if "diagnostics" in result:
            exp_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invariant,
                diagnostics=result["diagnostics"],
            )
            return create_response(400, json.dumps(exp_error))
        # Workaround for fhir.resources JSON removing the empty "entry" list.
        result_json_dict: dict = json.loads(result.json())
        if "entry" in result_json_dict:
            result_json_dict["entry"] = [
                entry
                for entry in result_json_dict["entry"]
                if entry["resource"].get("status") not in ("not-done", "entered-in-error")
            ]
            total_count = sum(1 for entry in result_json_dict["entry"] if entry.get("search", {}).get("mode") == "match")
            result_json_dict["total"] = total_count
            if request_contained_unauthorised_vaccs:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.warning,
                    code=Code.unauthorized,
                    diagnostics="Your search contains details that you are not authorised to request",
                )
                result_json_dict["entry"].append({"resource": exp_error})
        if "entry" not in result_json_dict:
            result_json_dict["entry"] = []
            result_json_dict["total"] = 0
        return create_response(200, json.dumps(result_json_dict))

    def _is_valid_immunization_id(self, immunization_id: str) -> bool:
        """Validates if the given unique Immunization ID is valid."""
        return False if not re.match(self._IMMUNIZATION_ID_PATTERN, immunization_id) else True

    def _validate_identifier_system(self, _id: str, _elements: str) -> Optional[dict]:
        if not _id:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=(
                    "Search parameter identifier must have one value and must be in the format of "
                    '"identifier.system|identifier.value" '
                    'e.g. "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
                ),
            )
        if "|" not in _id or " " in _id:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=(
                    "Search parameter identifier must be in the format of "
                    '"identifier.system|identifier.value" '
                    'e.g. "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
                ),
            )

        if not _elements:
            return None

        requested_elements = {e.strip().lower() for e in _elements.split(",") if e.strip()}
        requested_elements_valid = requested_elements.issubset({"id", "meta"})
        if _elements and not requested_elements_valid:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics="_elements must be one or more of the following: id,meta",
            )

    def _create_bad_request(self, message):
        error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=message,
        )
        return create_response(400, error)

    def fetch_identifier_system_and_element(self, event: dict):
        """
        Extracts `identifier` and `_elements` from an incoming FHIR search request.

        FHIR search supports two input formats:
        1. GET search: parameters appear in the query string (e.g. ?identifier=abc123&_elements=id,meta)
        2. POST search: parameters appear in the request body, form-encoded (e.g. identifier=abc123&_elements=id,meta)

        This function handles both cases, returning:
        - The extracted identifier value
        - The extracted _elements value
        - Any validation check result for disallowed keys
        - Booleans indicating whether identifier/_elements were present
        """

        query_params = event.get("queryStringParameters", {})
        body = event["body"]
        not_required_keys = [
            "-date.from",
            "-date.to",
            "-immunization.target",
            "_include",
            "patient.identifier",
        ]

        # Get Search Query Parameters
        if query_params and not body:
            query_string_has_immunization_identifier = "identifier" in query_params
            query_string_has_element = "_elements" in query_params
            identifier = query_params.get("identifier", "")
            element = query_params.get("_elements", "")
            query_check = check_keys_in_sources(event, not_required_keys)

            return (
                identifier,
                element,
                query_check,
                query_string_has_immunization_identifier,
                query_string_has_element,
            )

        # Post Search Identifier by body form
        if body and not query_params:
            decoded_body = base64.b64decode(body).decode("utf-8")
            parsed_body = urllib.parse.parse_qs(decoded_body)
            # Attempt to extract 'identifier' and '_elements'
            converted_identifier = ""
            converted_elements = ""
            identifier = parsed_body.get("identifier", "")
            if identifier:
                converted_identifier = "".join(identifier)
            _elements = parsed_body.get("_elements", "")
            if _elements:
                converted_elements = "".join(_elements)
            body_has_identifier = "identifier" in parsed_body
            body_has_immunization_elements = "_elements" in parsed_body
            body_check = check_keys_in_sources(event, not_required_keys)
            return (
                converted_identifier,
                converted_elements,
                body_check,
                body_has_identifier,
                body_has_immunization_elements,
            )

    def create_response_for_identifier(self, not_required, has_identifier, has_element):
        if "patient.identifier" in not_required and has_identifier:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter should have either identifier or patient.identifier",
            )
            return create_response(400, error)

        if not_required and has_element:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter _elements must have the following parameter: identifier",
            )
            return create_response(400, error)

    @staticmethod
    def _identify_supplier_system(aws_event):
        supplier_system = aws_event["headers"]["SupplierSystem"]
        if not supplier_system:
            raise UnauthorizedError()
        return supplier_system
