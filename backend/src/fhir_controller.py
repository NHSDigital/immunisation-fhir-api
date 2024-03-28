import base64
import json
import os
import re
import uuid
from decimal import Decimal
from typing import Optional
from urllib.parse import parse_qs

import boto3
from authorization import Authorization, EndpointOperation, UnknownPermission
from botocore.config import Config
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
    IdentifierDuplicationError
)
from pds_service import PdsService, Authenticator


def make_controller(
    pds_env: str = os.getenv("PDS_ENV", "int"),
    immunization_env: str = os.getenv("IMMUNIZATION_ENV")
):
    endpoint_url = "http://localhost:4566" if immunization_env == "local" else None
    imms_repo = ImmunizationRepository(create_table(endpoint_url=endpoint_url))
    boto_config = Config(region_name="eu-west-2")
    cache = Cache(directory="/tmp")
    authenticator = Authenticator(
        boto3.client("secretsmanager", config=boto_config), pds_env, cache
    )
    pds_service = PdsService(authenticator, pds_env)

    authorizer = Authorization()
    service = FhirService(imms_repo=imms_repo, pds_service=pds_service)

    return FhirController(authorizer=authorizer, fhir_service=service)


class FhirController:
    immunization_id_pattern = r"^[A-Za-z0-9\-.]{1,64}$"

    def __init__(self, authorizer: Authorization, fhir_service: FhirService):
        self.fhir_service = fhir_service
        self.authorizer = authorizer

    def get_immunization_by_id(self, aws_event) -> dict:
        
        if response := self.authorize_request(EndpointOperation.READ, aws_event):
            return response
        
        imms_id = aws_event["pathParameters"]["id"]

        if id_error := self._validate_id(imms_id):
            return self.create_response(400, id_error)

        if resource := self.fhir_service.get_immunization_by_id(imms_id):
            return FhirController.create_response(200, resource.json())
        else:
            msg = "The requested resource was not found."
            id_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.not_found,
                diagnostics=msg,
            )
            return FhirController.create_response(404, id_error)

    def create_immunization(self, aws_event):
        if response := self.authorize_request(EndpointOperation.CREATE, aws_event):
            return response

        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
        except json.decoder.JSONDecodeError as e:
            return self._create_bad_request(f"Request's body contains malformed JSON: {e}")

        try:
            resource = self.fhir_service.create_immunization(imms)
            location = f"{get_service_url()}/Immunization/{resource.id}"
            return self.create_response(201, None, {"Location": location})
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as invalid_error:
            return self.create_response(422, invalid_error.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())

    def update_immunization(self, aws_event):
        if response := self.authorize_request(EndpointOperation.UPDATE, aws_event):
            return response

        imms_id = aws_event["pathParameters"]["id"]
        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, json.dumps(id_error))
        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
        except json.decoder.JSONDecodeError as e:
            return self._create_bad_request(
                f"Request's body contains malformed JSON: {e}"
            )

        try:
            outcome, resource = self.fhir_service.update_immunization(imms_id, imms)
            if outcome == UpdateOutcome.UPDATE:
                return self.create_response(200)
            elif outcome == UpdateOutcome.CREATE:
                location = f"{get_service_url()}/Immunization/{resource.id}"
                return self.create_response(201, None, {"Location": location})
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as invalid_error:
            return self.create_response(422, invalid_error.to_operation_outcome())

    def delete_immunization(self, aws_event):
        if response := self.authorize_request(EndpointOperation.DELETE, aws_event):
            return response

        imms_id = aws_event["pathParameters"]["id"]

        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, id_error)

        try:
            self.fhir_service.delete_immunization(imms_id)
            return self.create_response(204)
        except ResourceNotFoundError as not_found:
            return self.create_response(404, not_found.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())

    def search_immunizations(self, aws_event) -> dict:
        if response := self.authorize_request(EndpointOperation.SEARCH, aws_event):
            return response

        http_method = aws_event.get("httpMethod")
        nhs_number_value = None
        disease_type_value = None
        nhs_number_param = "-nhsNumber"
        disease_type_param = "-diseaseType"
        if http_method == "POST":
            content_type = aws_event.get("headers", {}).get("Content-Type")
            if content_type == "application/x-www-form-urlencoded":
                body = aws_event.get("body")
                if body:
                    decoded_body = base64.b64decode(body).decode("utf-8")
                    parsed_body = parse_qs(decoded_body)
                    nhs_number_list = parsed_body.get(nhs_number_param)
                    if nhs_number_list:
                        nhs_number_value = nhs_number_list[0]
                    disease_type_list = parsed_body.get(disease_type_param)
                    if disease_type_list:
                        disease_type_value = disease_type_list[0]
        parsed_query_params = aws_event.get("queryStringParameters")
        if parsed_query_params:
            nhs_number_query_param_value = parsed_query_params.get(nhs_number_param)
            if nhs_number_query_param_value:
                if nhs_number_value is None:
                    nhs_number_value = nhs_number_query_param_value
                else:
                    if nhs_number_query_param_value != nhs_number_value:
                        return self._create_bad_request(
                            f"Search Parameter {nhs_number_param} can have only one value"
                        )

            disease_type_query_param_value = parsed_query_params.get(disease_type_param)
            if disease_type_query_param_value:
                if disease_type_value is None:
                    disease_type_value = disease_type_query_param_value
                else:
                    if disease_type_query_param_value != disease_type_value:
                        return self._create_bad_request(
                            f"Search Parameter {disease_type_param} can have only one value"
                        )
        if not nhs_number_value:
            return self._create_bad_request(
                f"Search Parameter {nhs_number_param} is mandatory"
            )
        if not disease_type_value:
            return self._create_bad_request(
                f"Search Parameter {disease_type_param} is mandatory"
            )

        search_params = f"{nhs_number_param}={nhs_number_value}&{disease_type_param}={disease_type_value}"
        result = self.fhir_service.search_immunizations(
            nhs_number_value, disease_type_value, search_params
        )
        return self.create_response(200, result.json())

    def _validate_id(self, _id: str) -> Optional[dict]:
        if not re.match(self.immunization_id_pattern, _id):
            msg = (
                "the provided event ID is either missing or not in the expected format."
            )
            return create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics=msg,
            )
        else:
            return None

    def _create_bad_request(self, message):
        error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=message,
        )
        return self.create_response(400, error)

    def authorize_request(self, operation: EndpointOperation, aws_event: dict) -> Optional[dict]:
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
                diagnostics='application includes invalid authorization values',
            )
            return self.create_response(500, id_error)

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
