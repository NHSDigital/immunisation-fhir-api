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
import boto3
from aws_lambda_typing.events import APIGatewayProxyEventV1
from botocore.config import Config
from fhir.resources.R4B.immunization import Immunization

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
    InconsistentIdError,
    UnauthorizedVaxError,
    UnauthorizedVaxOnRecordError,
    UnauthorizedSystemError
)

from pds_service import PdsService
from parameter_parser import process_params, process_search_params, create_query_string


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


    return FhirController(
        authorizer=authorizer, fhir_service=service)



class FhirController:
    immunization_id_pattern = r"^[A-Za-z0-9\-.]{1,64}$"


    def __init__(
        self,
        authorizer: Authorization,
        fhir_service: FhirService,
        ):
        self.fhir_service = fhir_service
        self.authorizer = authorizer
       

    def get_immunization_by_id(self, aws_event) -> dict:
        if response := self.authorize_request(EndpointOperation.READ, aws_event):
            return response

        imms_id = aws_event["pathParameters"]["id"]
        if id_error := self._validate_id(imms_id):
            return self.create_response(400, id_error)
        
        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                app_id = aws_event["headers"]["ApplicationId"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
                if len(app_id) == 0:
                    raise UnauthorizedSystemError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        
        try:
            if resource := self.fhir_service.get_immunization_by_id(imms_id, imms_vax_type_perms):
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
        if response := self.authorize_request(EndpointOperation.CREATE, aws_event):
            print(f"awsevent:{aws_event}")
            return response
        
        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                app_id = aws_event["headers"]["ApplicationId"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
                if len(app_id) == 0:
                    raise UnauthorizedSystemError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        
        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)            
        except json.decoder.JSONDecodeError as e:
            return self._create_bad_request(
                f"Request's body contains malformed JSON: {e}"
            )
            
        try:
            print("1")
            resource = self.fhir_service.create_immunization(imms,imms_vax_type_perms,app_id)
            print(f"resource:{resource}")
            if "diagnostics" in resource:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=resource["diagnostics"],
                )
                print(exp_error)
                return self.create_response(400, json.dumps(exp_error))
            location = f"{get_service_url()}/Immunization/{resource.id}"
            return self.create_response(201, None, {"Location": location})
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as duplicate:
            return self.create_response(422, duplicate.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def update_immunization(self, aws_event):
        if response := self.authorize_request(EndpointOperation.UPDATE, aws_event):
            return response
        imms_id = aws_event["pathParameters"]["id"]
        
        # Check vaxx type permissions- start
        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                app_id = aws_event["headers"]["ApplicationId"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
                if len(app_id) == 0:
                    raise UnauthorizedSystemError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Check vaxx type permissions- end
        
        # Validate the imms id -start
        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, json.dumps(id_error))
        # Validate the imms id -end

        # Validate the body of the request -start
        try:
            imms = json.loads(aws_event["body"], parse_float=Decimal)
            # Validate the imms id in the path params and body of request -start
            if imms.get("id", imms_id) != imms_id:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.invariant,
                    diagnostics=f"Validation errors: The provided immunization id:{imms_id} doesn't match with the content of the request body",
                )
                return self.create_response(400, json.dumps(exp_error))
            # Validate the imms id in the path params and body of request -end
        except json.decoder.JSONDecodeError as e:
            return self._create_bad_request(f"Request's body contains malformed JSON: {e}")
        # Validate the body of the request -end

        # Validate if the imms resource does not exists -start
        try:
            existing_record = self.fhir_service.get_immunization_by_id_all(imms_id,imms,app_id)
            if not existing_record:
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.error,
                    code=Code.not_found,
                    diagnostics=f"Validation errors: The requested immunization resource with id:{imms_id} was not found.",
                )
                return self.create_response(404, json.dumps(exp_error))
            
            if "error" in existing_record and existing_record is not None:
                   raise UnauthorizedSystemError
            if "diagnostics" in existing_record and existing_record is not None:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics=existing_record["diagnostics"],
                    )
                    return self.create_response(400, json.dumps(exp_error))
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
                return self.create_response(403, unauthorized.to_operation_outcome())
        # Validate if the imms resource does not exists -end
        
        # Check vaxx type permissions on the existing record - start
        try:
            vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
            vax_type_perm= self._vaccine_permission(existing_record["VaccineType"], "update")
            self._check_permission(vax_type_perm,vax_type_perms)
        except UnauthorizedVaxOnRecordError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        # Check vaxx type permissions on the existing record - end
        
        existing_resource_version = int(existing_record["Version"])
        try:
            # Validate if the imms resource to be updated is a logically deleted resource-start
            if existing_record["DeletedAt"] == True:

                outcome, resource = self.fhir_service.reinstate_immunization(
                    imms_id, imms, existing_resource_version, imms_vax_type_perms
                )

            # Validate if the imms resource to be updated is a logically deleted resource-end
            else:
                # Validate if imms resource version is part of the request -start
                if not "E-Tag" in aws_event["headers"]:
                    exp_error = create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.error,
                        code=Code.invariant,
                        diagnostics="Validation errors: Immunization resource version not specified in the request headers",
                    )
                    return self.create_response(400, json.dumps(exp_error))
                # Validate if imms resource version is part of the request -end

                # Validate the imms resource version provided in the request headers is per standard -start
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
                # Validate the imms resource version provided in the request headers is per standard -end

                # Validate if resource version has changed since last retrieve -start
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
                # Validate if resource version has changed since last retrieve -end

                # Check if the record is reinstated record -start
                if existing_record["Reinstated"] == True:
                    outcome, resource = self.fhir_service.update_reinstated_immunization(

                    imms_id, imms, existing_resource_version, imms_vax_type_perms
                    )
                else:
                    outcome, resource = self.fhir_service.update_immunization(
                        imms_id, imms, existing_resource_version, imms_vax_type_perms

                    )

                # Check if the record is reinstated record -end

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
                return self.create_response(200)
        except ValidationError as error:
            return self.create_response(400, error.to_operation_outcome())
        except IdentifierDuplicationError as duplicate:
            return self.create_response(422, duplicate.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())

    def delete_immunization(self, aws_event):
        if response := self.authorize_request(EndpointOperation.DELETE, aws_event):
            return response

        imms_id = aws_event["pathParameters"]["id"]

        if id_error := self._validate_id(imms_id):
            return FhirController.create_response(400, id_error)
        
        try:
            if aws_event.get("headers"):
                imms_vax_type_perms = aws_event["headers"]["VaccineTypePermissions"]
                app_id = aws_event["headers"]["ApplicationId"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
                if len(app_id) == 0:
                    raise UnauthorizedSystemError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
         
        try:
            self.fhir_service.delete_immunization(imms_id, imms_vax_type_perms,app_id)
            return self.create_response(204)
        except ResourceNotFoundError as not_found:
            return self.create_response(404, not_found.to_operation_outcome())
        except UnhandledResponseError as unhandled_error:
            return self.create_response(500, unhandled_error.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
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
                app_id = aws_event["headers"]["ApplicationId"]
                if len(imms_vax_type_perms) == 0:
                    raise UnauthorizedVaxError()
                if len(app_id) == 0:
                    raise UnauthorizedSystemError()
            else:
                raise UnauthorizedError()
        except UnauthorizedError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedVaxError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())
        except UnauthorizedSystemError as unauthorized:
            return self.create_response(403, unauthorized.to_operation_outcome())    
        # Check vaxx type permissions on the existing record - start
        try:
            vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
            vax_type_perm= self._new_vaccine_request(search_params.immunization_targets, "search", vax_type_perms)
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
            search_params.date_to
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
                if entry["resource"].get("status") not in ("not-done", "entered-in-error")
            ]
            total_count = sum(
                1 for entry in result_json_dict["entry"] if entry.get("search", {}).get("mode") == "match"
            )
            result_json_dict["total"] = total_count
            if sorted(search_params.immunization_targets) != sorted(vax_type_perm):
                exp_error = create_operation_outcome(
                    resource_id=str(uuid.uuid4()),
                    severity=Severity.warning,
                    code=Code.unauthorized,
                    diagnostics="Your search contains details that you are not authorised to request"
                )
                result_json_dict['entry'].append({'resource': exp_error})
        if "entry" not in result_json_dict:
            result_json_dict["entry"] = []
            result_json_dict["total"] = 0
        return self.create_response(200, json.dumps(result_json_dict))

    def _validate_id(self, _id: str) -> Optional[dict]:
        if not re.match(self.immunization_id_pattern, _id):
            msg = "the provided event ID is either missing or not in the expected format."
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
                diagnostics="application includes invalid authorization values",
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
        
    @staticmethod
    def _vaccine_permission( vaccine_type, operation) -> set:
        vaccine_permission = set()
        if isinstance(vaccine_type, list):
            for x in vaccine_type:
                vaccine_permission.add(str.lower(f"{x}:{operation}"))
            return vaccine_permission    
        else:
            vaccine_permission.add(str.lower(f"{vaccine_type}:{operation}"))
            return vaccine_permission
    
    @staticmethod
    def _parse_vaccine_permissions(imms_vax_type_perms) -> set:
        parsed = [str.strip(str.lower(s)) for s in imms_vax_type_perms.split(",")]
        vaccine_permissions = set()
        for s in parsed:
            vaccine_permissions.add(s)
        return vaccine_permissions
    
    @staticmethod
    def _check_permission( requested: set, allowed: set) -> set:
        if not requested.issubset(allowed):
            raise UnauthorizedVaxOnRecordError()
        else:
            return None

    @staticmethod    
    def _new_vaccine_request( vaccine_type, operation, vaccine_type_permissions: None) -> Optional[list]:
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
