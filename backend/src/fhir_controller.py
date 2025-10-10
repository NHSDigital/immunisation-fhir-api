import base64
import json
import os
import re
import uuid
from decimal import Decimal
from typing import Optional
from aws_lambda_typing.events import APIGatewayProxyEventV1
from fhir.resources.R4B.immunization import Immunization
from boto3 import client as boto3_client

from fhir_repository import ImmunizationRepository, create_table
from fhir_service import FhirService, UpdateOutcome, get_service_url
from models.errors import (
    Severity,
    Code,
    create_operation_outcome,
    UnauthorizedError,
    ResourceNotFoundError,
    UnhandledResponseError,
    ValidationError,
    IdentifierDuplicationError,
    ParameterException,
    UnauthorizedVaxError,
)
from models.utils.generic_utils import check_keys_in_sources
from parameter_parser import process_params, process_search_params, create_query_string
import urllib.parse

sqs_client = boto3_client("sqs", region_name="eu-west-2")
queue_url = os.getenv("SQS_QUEUE_URL", "Queue_url")


def make_controller(
    immunization_env: str = os.getenv("IMMUNIZATION_ENV"),
):
    endpoint_url = "http://localhost:4566" if immunization_env == "local" else None
    imms_repo = ImmunizationRepository(create_table(endpoint_url=endpoint_url))

    service = FhirService(imms_repo=imms_repo)

    return FhirController(fhir_service=service)


class FhirController:
    immunization_id_pattern = r"^[A-Za-z0-9\-.]{1,64}$"

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
            return self.create_response(403, unauthorized.to_operation_outcome())
        body = aws_event["body"]
        if query_params and body:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=('Parameters may not be duplicated. Use commas for "or".'),
            )
            return self.create_response(400, error)
        identifier, element, not_required, has_imms_identifier, has_element = self.fetch_identifier_system_and_element(
            aws_event
        )
        if not_required:
            return self.create_response_for_identifier(not_required, has_imms_identifier, has_element)
        # If not found, retrieve from multiValueQueryStringParameters
        if id_error := self._validate_identifier_system(identifier, element):
            return self.create_response(400, id_error)
        identifiers = identifier.replace("|", "#")
        supplier_system = self._identify_supplier_system(aws_event)

        try:
            if resource := self.fhir_service.get_immunization_by_identifier(
                identifiers, supplier_system, identifier, element
            ):
                return FhirController.create_response(200, resource)
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def get_immunization_by_id(self, aws_event) -> dict:
        imms_id = aws_event["pathParameters"]["id"]
        if id_error := self._validate_id(imms_id):
            return self.create_response(400, id_error)

        try:
            if aws_event.get("headers"):
                supplier_system = self._identify_supplier_system(aws_event)
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        try:
            if resource := self.fhir_service.get_immunization_by_id(imms_id, supplier_system):
                version = str()
                if isinstance(resource, Immunization):
                    resp = resource
                else:
                    resp = resource["Resource"]
                    if resource.get("Version"):
                        version = resource["Version"]
                return FhirController.create_response(200, resp.json(), {"E-Tag": version})
            else:
                msg = "The requested resource was not found."
                id_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.not_found,
                    diagnostics=msg,
                )
                return FhirController.create_response(404, id_error)
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def create_immunization(self, aws_event):
        if not aws_event.get("headers"):
            return self.create_response(
                403,
                create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.forbidden,
                    diagnostics="Unauthorized request",
                ),
            )

        supplier_system = self._identify_supplier_system(aws_event)

        try:
            immunisation = json.loads(aws_event["body"], parse_float=Decimal)
        except json.decoder.JSONDecodeError as e:
            return self._create_bad_request(f"Request's body contains malformed JSON: {e}")
        try:
            resource = self.fhir_service.create_immunization(immunisation, supplier_system)
            if "diagnostics" in resource:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=resource["diagnostics"],
                )
                return self.create_response(400, json.dumps(exp_error))
            else:
                location = f"{get_service_url()}/Immunization/{resource.id}"
                version = "1"
                return self.create_response(201, None, {"Location": location, "E-Tag": version})
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as duplicate:
            return self.create_response(422, duplicate.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def update_immunization(self, aws_event):
        try:
            if aws_event.get("headers"):
                imms_id = aws_event["pathParameters"]["id"]
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        supplier_system = self._identify_supplier_system(aws_event)

        # Validate the imms id - start
        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, json.dumps(id_error))
        # Validate the imms id - end

        # Validate the body of the request - start
        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
            # Validate the imms id in the path params and body of request - start
            if imms.get("id") != imms_id:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=f"Validation errors: The provided immunization id:{imms_id} doesn't match with the content of the request body",
                )
                return self.create_response(400, json.dumps(exp_error))
            # Validate the imms id in the path params and body of request - end
        except json.decoder.JSONDecodeError as e:
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
                    diagnostics=f"Validation errors: The requested immunization resource with id:{imms_id} was not found.",
                )
                return self.create_response(404, json.dumps(exp_error))

            if "diagnostics" in existing_record:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=existing_record["diagnostics"],
                )
                return self.create_response(400, json.dumps(exp_error))
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        # Validate if the imms resource does not exist - end

        existing_resource_version = int(existing_record["Version"])
        existing_resource_vacc_type = existing_record["VaccineType"]

        try:
            # Validate if the imms resource to be updated is a logically deleted resource - start
            if existing_record["DeletedAt"]:
                outcome, resource, updated_version = self.fhir_service.reinstate_immunization(
                    imms_id, imms, existing_resource_version, existing_resource_vacc_type, supplier_system
                )
            # Validate if the imms resource to be updated is a logically deleted resource-end
            else:
                # Validate if imms resource version is part of the request - start
                if "E-Tag" not in aws_event["headers"]:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics="Validation errors: Immunization resource version not specified in the request headers",
                    )
                    return self.create_response(400, json.dumps(exp_error))
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
                        diagnostics=f"Validation errors: Immunization resource version:{resource_version} in the request headers is invalid.",
                    )
                    return self.create_response(400, json.dumps(exp_error))
                # Validate the imms resource version provided in the request headers - end

                # Validate if resource version has changed since the last retrieve - start
                if existing_resource_version > resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=f"Validation errors: The requested immunization resource {imms_id} has changed since the last retrieve.",
                    )
                    return self.create_response(400, json.dumps(exp_error))
                if existing_resource_version < resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=f"Validation errors: The requested immunization resource {imms_id} version is inconsistent with the existing version.",
                    )
                    return self.create_response(400, json.dumps(exp_error))
                # Validate if resource version has changed since the last retrieve - end

                # Check if the record is reinstated record - start
                if existing_record["Reinstated"] is True:
                    outcome, resource, updated_version = self.fhir_service.update_reinstated_immunization(
                        imms_id, imms, existing_resource_version, existing_resource_vacc_type, supplier_system
                    )
                else:
                    outcome, resource, updated_version = self.fhir_service.update_immunization(
                        imms_id, imms, existing_resource_version, existing_resource_vacc_type, supplier_system
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
                return self.create_response(400, json.dumps(exp_error))
            if outcome == UpdateOutcome.UPDATE:
                return self.create_response(
                    200, None, {"E-Tag": updated_version}
                )  # include e-tag here, is it not included in the response resource
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as duplicate:
            return self.create_response(422, duplicate.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def delete_immunization(self, aws_event):
        try:
            if aws_event.get("headers"):
                imms_id = aws_event["pathParameters"]["id"]
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        # Validate the imms id
        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, json.dumps(id_error))

        supplier_system = self._identify_supplier_system(aws_event)

        try:
            self.fhir_service.delete_immunization(imms_id, supplier_system)
            return self.create_response(204)

        except ResourceNotFoundError as not_found:
            return self.create_response(404, not_found.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

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
            return self.create_response(403, unauthorized.to_operation_outcome())

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
            return self.create_response(403, unauthorized.to_operation_outcome())

        if "diagnostics" in result:
            exp_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invariant,
                diagnostics=result["diagnostics"],
            )
            return self.create_response(400, json.dumps(exp_error))
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
        return self.create_response(200, json.dumps(result_json_dict))

    def _validate_id(self, _id: str) -> Optional[dict]:
        if not re.match(self.immunization_id_pattern, _id):
            msg = "Validation errors: the provided event ID is either missing or not in the expected format."
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=msg,
            )
        else:
            return None

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
        return self.create_response(400, error)

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
        not_required_keys = ["-date.from", "-date.to", "-immunization.target", "_include", "patient.identifier"]

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
            return self.create_response(400, error)

        if not_required and has_element:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter _elements must have the following parameter: identifier",
            )
            return self.create_response(400, error)

    @staticmethod
    def create_response(status_code, body=None, headers=None):
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            if headers:
                headers["Content-Type"] = "application/fhir+json"
            else:
                headers = {"Content-Type": "application/fhir+json"}

        return {
            "statusCode": status_code,
            "headers": headers if headers else {},
            **({"body": body} if body else {}),
        }

    @staticmethod
    def _identify_supplier_system(aws_event):
        supplier_system = aws_event["headers"]["SupplierSystem"]
        if not supplier_system:
            raise UnauthorizedError("SupplierSystem header is missing")
        return supplier_system
