import base64
import boto3
import json
import os
import re
import uuid
from botocore.config import Config
from decimal import Decimal
from typing import Optional
from authentication import AppRestrictedAuth, Service
from aws_lambda_typing.events import APIGatewayProxyEventV1
from fhir.resources.R4B.immunization import Immunization
from boto3 import client as boto3_client

from authorization import Authorization, EndpointOperation, UnknownPermission
from cache import Cache
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
    UnauthorizedVaxOnRecordError,
    UnauthorizedSystemError,
)
from models.utils.generic_utils import check_keys_in_sources
from pds_service import PdsService
from parameter_parser import process_params, process_search_params, create_query_string
import urllib.parse

sqs_client = boto3_client("sqs", region_name="eu-west-2")
queue_url = os.getenv("SQS_QUEUE_URL", "Queue_url")


def make_controller(
    pds_env: str = os.getenv("PDS_ENV", "int"),
    immunization_env: str = os.getenv("IMMUNIZATION_ENV"),
):
    endpoint_url = "http://localhost:4566" if immunization_env == "local" else None
    imms_repo = ImmunizationRepository(create_table(endpoint_url=endpoint_url))
    boto_config = Config(region_name="eu-west-2")
    cache = Cache(directory="/tmp")
    authenticator = AppRestrictedAuth(
        service=Service.PDS,
        secret_manager_client=boto3.client("secretsmanager", config=boto_config),
        environment=pds_env,
        cache=cache,
    )
    pds_service = PdsService(authenticator, pds_env)

    authorizer = Authorization()
    service = FhirService(imms_repo=imms_repo, pds_service=pds_service)

    return FhirController(authorizer=authorizer, fhir_service=service)


class FhirController:
    immunization_id_pattern = r"^[A-Za-z0-9\-.]{1,64}$"

    def __init__(
        self,
        authorizer: Authorization,
        fhir_service: FhirService,
    ):
        self.fhir_service = fhir_service
        self.authorizer = authorizer

    def get_immunization_by_identifier(self, aws_event) -> dict:
        try:
            if aws_event.get("headers"):
                is_imms_batch_app = (
                    aws_event["headers"]["SupplierSystem"] == "Imms-Batch-App"
                )
                if not is_imms_batch_app:
                    if response := self.authorize_request(
                        EndpointOperation.SEARCH, aws_event
                    ):
                        return response
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
        identifier, element, not_required, has_imms_identifier, has_element = (
            self.fetch_identifier_system_and_element(aws_event)
        )
        if not_required:
            return self.create_response_for_identifier(
                not_required, has_imms_identifier, has_element
            )
        # If not found, retrieve from multiValueQueryStringParameters
        if id_error := self._validate_identifier_system(identifier, element):
            return self.create_response(400, id_error)
        identifiers = identifier.replace("|", "#")
        try:
            imms_vax_type_perms = None
            if not is_imms_batch_app:
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        try:
            if resource := self.fhir_service.get_immunization_by_identifier(
                identifiers, imms_vax_type_perms, identifier, element, is_imms_batch_app
            ):
                return FhirController.create_response(200, resource)
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def get_immunization_by_id(self, aws_event) -> dict:
        if response := self.authorize_request(EndpointOperation.READ, aws_event):
            return response

        imms_id = aws_event["pathParameters"]["id"]
        if id_error := self._validate_id(imms_id):
            return self.create_response(400, id_error)

        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        try:
            if resource := self.fhir_service.get_immunization_by_id(
                imms_id, imms_vax_type_perms
            ):
                version = str()
                if isinstance(resource, Immunization):
                    resp = resource
                else:
                    resp = resource["Resource"]
                    if resource.get("Version"):
                        version = resource["Version"]
                return FhirController.create_response(
                    200, resp.json(), {"E-Tag": version}
                )
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
        try:
            file_name = ""
            message_id = ""
            if aws_event.get("headers"):
                is_imms_batch_app = (
                    aws_event["headers"]["SupplierSystem"] == "Imms-Batch-App"
                )
                if is_imms_batch_app:
                    file_name = aws_event["headers"]["file_key"]
                    message_id = aws_event["headers"]["row_id"]
                    created_at_formatted_string = aws_event["headers"][
                        "created_at_formatted_string"
                    ]
                    local_id = aws_event["headers"]["local_id"]
                    operation_requested = aws_event["headers"]["operation_requested"]
                    aws_event["body"] = json.dumps(aws_event["body"])
                else:
                    if response := self.authorize_request(
                        EndpointOperation.CREATE, aws_event
                    ):
                        return response
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        # Call the common method and unpack the results
        response, imms_vax_type_perms, supplier_system = (
            self.check_vaccine_type_permissions(aws_event, is_imms_batch_app)
        )
        if response:
            return response

        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
        except json.decoder.JSONDecodeError as e:
            final_resp = self._create_bad_request(
                f"Request's body contains malformed JSON: {e}"
            )
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp

        try:
            resource = self.fhir_service.create_immunization(
                imms, imms_vax_type_perms, supplier_system, is_imms_batch_app
            )
            if "diagnostics" in resource:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=resource["diagnostics"],
                )
                final_resp = self.create_response(400, json.dumps(exp_error))
            else:
                location = f"{get_service_url()}/Immunization/{resource.id}"
                final_resp = self.create_response(201, None, {"Location": location})

            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except ValidationError as error:
            final_resp = self.create_response(400, error.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except IdentifierDuplicationError as duplicate:
            final_resp = self.create_response(422, duplicate.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except UnhandledResponseError as unhandled_error:
            final_resp = self.create_response(
                500, unhandled_error.to_operation_outcome()
            )
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def update_immunization(self, aws_event):
        try:
            file_name = ""
            message_id = ""
            if aws_event.get("headers"):
                is_imms_batch_app = (
                    aws_event["headers"]["SupplierSystem"] == "Imms-Batch-App"
                )
                if is_imms_batch_app:
                    file_name = aws_event["headers"]["file_key"]
                    message_id = aws_event["headers"]["row_id"]
                    created_at_formatted_string = aws_event["headers"][
                        "created_at_formatted_string"
                    ]
                    local_id = aws_event["headers"]["local_id"]
                    operation_requested = aws_event["headers"]["operation_requested"]
                    aws_event["body"] = json.dumps(aws_event["body"])
                else:
                    if response := self.authorize_request(
                        EndpointOperation.UPDATE, aws_event
                    ):
                        return response
                imms_id = aws_event["pathParameters"]["id"]
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Call the common method and unpack the results
        response, imms_vax_type_perms, supplier_system = (
            self.check_vaccine_type_permissions(aws_event, is_imms_batch_app)
        )
        if response:
            return response

        # Validate the imms id - start
        if id_error := self._validate_id(imms_id):
            final_resp = FhirController.create_response(400, json.dumps(id_error))
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
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
                final_resp = self.create_response(400, json.dumps(exp_error))
                if is_imms_batch_app:
                    self._sendack(
                        final_resp,
                        file_name,
                        message_id,
                        created_at_formatted_string,
                        local_id,
                        operation_requested,
                    )
                return final_resp
            # Validate the imms id in the path params and body of request - end
        except json.decoder.JSONDecodeError as e:
            final_resp = self._create_bad_request(
                f"Request's body contains malformed JSON: {e}"
            )
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except Exception as e:
            final_resp = self._create_bad_request(
                f"Request's body contains string: {e}"
            )
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        # Validate the body of the request - end

        # Validate if the imms resource does not exist - start
        try:
            existing_record = self.fhir_service.get_immunization_by_id_all(
                imms_id, imms
            )
            if not existing_record:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.not_found,
                    diagnostics=f"Validation errors: The requested immunization resource with id:{imms_id} was not found.",
                )
                final_resp = self.create_response(404, json.dumps(exp_error))
                if is_imms_batch_app:
                    self._sendack(
                        final_resp,
                        file_name,
                        message_id,
                        created_at_formatted_string,
                        local_id,
                        operation_requested,
                    )
                return final_resp

            if "diagnostics" in existing_record and existing_record is not None:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=existing_record["diagnostics"],
                )
                final_resp = self.create_response(400, json.dumps(exp_error))
                if is_imms_batch_app:
                    self._sendack(
                        final_resp,
                        file_name,
                        message_id,
                        created_at_formatted_string,
                        local_id,
                        operation_requested,
                    )
                return final_resp
        except ValidationError as error:
            final_resp = self.create_response(400, error.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        # Validate if the imms resource does not exist - end

        # Check vaccine type permissions on the existing record - start
        try:
            if not is_imms_batch_app:
                vax_type_perms = self._parse_vaccine_permissions_controller(
                    imms_vax_type_perms
                )
                vax_type_perm = self._vaccine_permission(
                    existing_record["VaccineType"], "update"
                )
                self._check_permission(vax_type_perm, vax_type_perms)
        except UnauthorizedVaxOnRecordError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Check vaccine type permissions on the existing record - end

        existing_resource_version = int(existing_record["Version"])
        try:
            # Validate if the imms resource to be updated is a logically deleted resource - start
            if existing_record["DeletedAt"] is True:

                outcome, resource = self.fhir_service.reinstate_immunization(
                    imms_id,
                    imms,
                    existing_resource_version,
                    imms_vax_type_perms,
                    supplier_system,
                    is_imms_batch_app,
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
                    final_resp = self.create_response(400, json.dumps(exp_error))
                    if is_imms_batch_app:
                        self._sendack(
                            final_resp,
                            file_name,
                            message_id,
                            created_at_formatted_string,
                            local_id,
                            operation_requested,
                        )
                    return final_resp
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
                    final_resp = self.create_response(400, json.dumps(exp_error))
                    if is_imms_batch_app:
                        self._sendack(
                            final_resp,
                            file_name,
                            message_id,
                            created_at_formatted_string,
                            local_id,
                            operation_requested,
                        )
                    return final_resp
                # Validate the imms resource version provided in the request headers - end

                # Validate if resource version has changed since the last retrieve - start
                if existing_resource_version > resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=f"Validation errors: The requested immunization resource {imms_id} has changed since the last retrieve.",
                    )
                    final_resp = self.create_response(400, json.dumps(exp_error))
                    if is_imms_batch_app:
                        self._sendack(
                            final_resp,
                            file_name,
                            message_id,
                            created_at_formatted_string,
                            local_id,
                            operation_requested,
                        )
                    return final_resp

                if existing_resource_version < resource_version_header:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=f"Validation errors: The requested immunization resource {imms_id} version is inconsistent with the existing version.",
                    )
                    final_resp = self.create_response(400, json.dumps(exp_error))
                    if is_imms_batch_app:
                        self._sendack(
                            final_resp,
                            file_name,
                            message_id,
                            created_at_formatted_string,
                            local_id,
                            operation_requested,
                        )
                    return final_resp
                # Validate if resource version has changed since the last retrieve - end

                # Check if the record is reinstated record - start
                if existing_record["Reinstated"] is True:
                    outcome, resource = (
                        self.fhir_service.update_reinstated_immunization(
                            imms_id,
                            imms,
                            existing_resource_version,
                            imms_vax_type_perms,
                            supplier_system,
                            is_imms_batch_app,
                        )
                    )
                else:
                    outcome, resource = self.fhir_service.update_immunization(
                        imms_id,
                        imms,
                        existing_resource_version,
                        imms_vax_type_perms,
                        supplier_system,
                        is_imms_batch_app,
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
                final_resp = self.create_response(400, json.dumps(exp_error))
                if is_imms_batch_app:
                    self._sendack(
                        final_resp,
                        file_name,
                        message_id,
                        created_at_formatted_string,
                        local_id,
                        operation_requested,
                    )
                return final_resp
            if outcome == UpdateOutcome.UPDATE:
                final_resp = self.create_response(200)
                if is_imms_batch_app:
                    self._sendack(
                        final_resp,
                        file_name,
                        message_id,
                        created_at_formatted_string,
                        local_id,
                        operation_requested,
                    )
                return final_resp
        except ValidationError as error:
            final_resp = self.create_response(400, error.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except IdentifierDuplicationError as duplicate:
            final_resp = self.create_response(422, duplicate.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def delete_immunization(self, aws_event):
        try:
            file_name = ""
            message_id = ""
            if aws_event.get("headers"):
                is_imms_batch_app = (
                    aws_event["headers"]["SupplierSystem"] == "Imms-Batch-App"
                )
                if is_imms_batch_app:
                    file_name = aws_event["headers"]["file_key"]
                    message_id = aws_event["headers"]["row_id"]
                    created_at_formatted_string = aws_event["headers"][
                        "created_at_formatted_string"
                    ]
                    local_id = aws_event["headers"]["local_id"]
                    operation_requested = aws_event["headers"]["operation_requested"]
                else:
                    if response := self.authorize_request(
                        EndpointOperation.DELETE, aws_event
                    ):
                        return response
                imms_id = aws_event["pathParameters"]["id"]
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

        # Validate the imms id - start
        if id_error := self._validate_id(imms_id):
            final_resp = FhirController.create_response(400, json.dumps(id_error))
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        # Validate the imms id - end

        # Call the common method and unpack the results
        response, imms_vax_type_perms, supplier_system = (
            self.check_vaccine_type_permissions(aws_event, is_imms_batch_app)
        )
        if response:
            return response

        try:
            self.fhir_service.delete_immunization(
                imms_id, imms_vax_type_perms, supplier_system, is_imms_batch_app
            )
            final_resp = self.create_response(204)
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp

        except ResourceNotFoundError as not_found:
            final_resp = self.create_response(404, not_found.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except UnhandledResponseError as unhandled_error:
            final_resp = self.create_response(
                500, unhandled_error.to_operation_outcome()
            )
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp
        except UnauthorizedVaxError as unauthorized:
            final_resp = self.create_response(403, unauthorized.to_operation_outcome())
            if is_imms_batch_app:
                self._sendack(
                    final_resp,
                    file_name,
                    message_id,
                    created_at_formatted_string,
                    local_id,
                    operation_requested,
                )
            return final_resp

    def search_immunizations(self, aws_event: APIGatewayProxyEventV1) -> dict:
        if response := self.authorize_request(EndpointOperation.SEARCH, aws_event):
            return response

        try:
            search_params = process_search_params(process_params(aws_event))
        except ParameterException as e:
            return self._create_bad_request(e.message)
        if search_params is None:
            raise Exception("Failed to parse parameters.")

        # Check vaxx type permissions- start
        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Check vaxx type permissions on the existing record - start
        try:
            vax_type_perms = self._parse_vaccine_permissions_controller(
                imms_vax_type_perms
            )
            vax_type_perm = self._new_vaccine_request(
                search_params.immunization_targets, "search", vax_type_perms
            )
            if not vax_type_perm:
                raise UnauthorizedVaxError
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Check vaxx type permissions on the existing record - end

        result = self.fhir_service.search_immunizations(
            search_params.patient_identifier,
            vax_type_perm,
            create_query_string(search_params),
            search_params.date_from,
            search_params.date_to,
        )

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
                if entry["resource"].get("status")
                not in ("not-done", "entered-in-error")
            ]
            total_count = sum(
                1
                for entry in result_json_dict["entry"]
                if entry.get("search", {}).get("mode") == "match"
            )
            result_json_dict["total"] = total_count
            if sorted(search_params.immunization_targets) != sorted(vax_type_perm):
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

    def _validate_identifier_system(self, _id: str, _element: str) -> Optional[dict]:

        if not _id:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=(
                    "Search parameter immunization.identifier must have one value and must be in the format of "
                    '"immunization.identifier.system|immunization.identifier.value" '
                    'e.g. "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
                ),
            )
        if "|" not in _id or " " in _id:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=(
                    "Search parameter immunization.identifier must be in the format of "
                    '"immunization.identifier.system|immunization.identifier.value" '
                    'e.g. "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
                ),
            )
        if not _element:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics="_element must be one or more of the following: id,meta",
            )
        element_lower = _element.lower()
        result = element_lower.split(",")
        is_present = all(key in ["id", "meta"] for key in result)
        if not is_present:
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics="_element must be one or more of the following: id,meta",
            )

    def _create_bad_request(self, message):
        error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=message,
        )
        return self.create_response(400, error)

    def authorize_request(
        self, operation: EndpointOperation, aws_event: dict
    ) -> Optional[dict]:
        try:
            self.authorizer.authorize(operation, aws_event)
        except UnauthorizedError as e:
            return self.create_response(403, e.to_operation_outcome())
        except UnknownPermission:
            # TODO: I think when AuthenticationType is not present, then we don't get below message. Double check again
            id_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="application includes invalid authorization values",
            )
            return self.create_response(500, id_error)

    def fetch_identifier_system_and_element(self, event: dict):
        query_params = event.get("queryStringParameters", {})
        body = event["body"]
        not_required_keys = [
            "-date.from",
            "-date.to",
            "-immunization.target",
            "_include",
            "patient.identifier",
        ]
        if query_params and not body:
            # Check for the presence of 'immunization.identifier' and '_element'
            query_string_has_immunization_identifier = (
                "immunization.identifier" in event.get("queryStringParameters", {})
            )
            query_string_has_element = "_element" in event.get(
                "queryStringParameters", {}
            )
            immunization_identifier = query_params.get("immunization.identifier", "")
            element = query_params.get("_element", "")
            query_check = check_keys_in_sources(event, not_required_keys)

            return (
                immunization_identifier,
                element,
                query_check,
                query_string_has_immunization_identifier,
                query_string_has_element,
            )
        if body and not query_params:
            decoded_body = base64.b64decode(body).decode("utf-8")
            parsed_body = urllib.parse.parse_qs(decoded_body)
            # Attempt to extract 'immunization.identifier' and '_element'
            converted_identifer = ""
            converted_element = ""
            immunization_identifier = parsed_body.get("immunization.identifier", "")
            if immunization_identifier:
                converted_identifer = "".join(immunization_identifier)
            _element = parsed_body.get("_element", "")
            if _element:
                converted_element = "".join(_element)
            body_has_immunization_identifier = "immunization.identifier" in parsed_body
            body_has_immunization_element = "_element" in parsed_body
            body_check = check_keys_in_sources(event, not_required_keys)
            return (
                converted_identifer,
                converted_element,
                body_check,
                body_has_immunization_identifier,
                body_has_immunization_element,
            )

    def create_response_for_identifier(self, not_required, has_identifier, has_element):
        if "patient.identifier" in not_required and has_identifier:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter should have either immunization.identifier or patient.identifier",
            )
            return self.create_response(400, error)

        if "patient.identifier" not in not_required and not_required and has_identifier:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter immunization.identifier must have the following parameter: _element",
            )
            return self.create_response(400, error)

        if not_required and has_element:
            error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics="Search parameter _element must have  the following parameter: immunization.identifier",
            )
            return self.create_response(400, error)

    def check_vaccine_type_permissions(self, aws_event, is_imms_batch_app):
        try:
            imms_vax_type_perms = None
            if not is_imms_batch_app:
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()

            supplier_system = self._identify_supplier_system(aws_event)
            if len(supplier_system) == 0:
                raise UnauthorizedSystemError()

            # Return the values needed for later use
            return None, imms_vax_type_perms, supplier_system

        except UnauthorizedVaxError as unauthorized:
            return (
                self.create_response(403, unauthorized.to_operation_outcome()),
                None,
                None,
            )
        except UnauthorizedSystemError as unauthorized:
            return (
                self.create_response(403, unauthorized.to_operation_outcome()),
                None,
                None,
            )
        except UnauthorizedError as e:
            return self._create_bad_request(str(e)), None, None

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
    def _sendack(
        payload,
        file_name,
        message_id,
        created_at_formatted_string,
        local_id,
        operation_requested,
    ):
        payload["file_key"] = file_name
        payload["row_id"] = message_id
        payload["created_at_formatted_string"] = created_at_formatted_string
        payload["local_id"] = local_id
        payload["operation_requested"] = operation_requested
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload),
            MessageGroupId=file_name,
        )

    @staticmethod
    def _vaccine_permission(vaccine_type, operation) -> set:
        vaccine_permission = set()
        if isinstance(vaccine_type, list):
            for x in vaccine_type:
                vaccine_permission.add(str.lower(f"{x}:{operation}"))
            return vaccine_permission
        else:
            vaccine_permission.add(str.lower(f"{vaccine_type}:{operation}"))
            return vaccine_permission

    @staticmethod
    def _parse_vaccine_permissions_controller(imms_vax_type_perms) -> set:
        parsed = [str.strip(str.lower(s)) for s in imms_vax_type_perms.split(",")]
        vaccine_permissions = set()
        for s in parsed:
            vaccine_permissions.add(s)
        return vaccine_permissions

    @staticmethod
    def _check_permission(requested: set, allowed: set) -> set:
        if not requested.issubset(allowed):
            raise UnauthorizedVaxOnRecordError()
        else:
            return None

    @staticmethod
    def _new_vaccine_request(
        vaccine_type, operation, vaccine_type_permissions: None
    ) -> Optional[list]:
        vaccine_permission = list()
        if isinstance(vaccine_type, list):
            for x in vaccine_type:
                vaccs_prms = set()
                vaccs_prms.add(str.lower(f"{x}:{operation}"))
                if vaccs_prms.issubset(vaccine_type_permissions):
                    vaccine_permission.append(x)
            return vaccine_permission
        else:
            return vaccine_permission

    @staticmethod
    def _identify_supplier_system(aws_event):
        supplier_system = aws_event["headers"]["SupplierSystem"]
        # supplier_system is obtained from the app. For batch app, need to look for the BatchSupplierSystem
        if "Imms-Batch-App" in supplier_system:
            supplier_system = aws_event["headers"]["BatchSupplierSystem"]
        return supplier_system
