import simplejson as json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Attr, Key
from models.utils.permission_checker import ApiOperationCode, validate_permissions
from botocore.config import Config
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    IdentifierDuplicationError,
    UnauthorizedVaxError,
)
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

from models.utils.validation_utils import get_vaccine_type, check_identifier_system_value


def create_table(table_name=None, endpoint_url=None, region_name="eu-west-2"):
    if not table_name:
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
    config = Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1})
    db: DynamoDBServiceResource = boto3.resource(
        "dynamodb", endpoint_url=endpoint_url, region_name=region_name, config=config
    )
    return db.Table(table_name)


def _make_immunization_pk(_id: str):
    return f"Immunization#{_id}"


def _make_patient_pk(_id: str):
    return f"Patient#{_id}"


def _query_identifier(table, index, pk, identifier):
    queryresponse = table.query(IndexName=index, KeyConditionExpression=Key(pk).eq(identifier), Limit=1)
    if queryresponse.get("Count", 0) > 0:
        return queryresponse


def get_nhs_number(imms):
    try:
        nhs_number = [x for x in imms["contained"] if x["resourceType"] == "Patient"][0]["identifier"][0]["value"]
    except (KeyError, IndexError):
        nhs_number = "TBC"
    return nhs_number


@dataclass
class RecordAttributes:
    pk: str
    patient_pk: str
    patient_sk: str
    resource: dict
    patient: dict
    vaccine_type: str
    timestamp: int
    identifier: str

    def __init__(self, imms: dict, patient: any):
        """Create attributes that may be used in dynamodb table"""
        imms_id = imms["id"]
        self.pk = _make_immunization_pk(imms_id)
        if patient or imms:
            nhs_number = get_nhs_number(imms)
        self.patient_pk = _make_patient_pk(nhs_number)
        self.patient = patient
        self.resource = imms
        self.timestamp = int(time.time())
        self.vaccine_type = get_vaccine_type(imms)
        self.system_id = imms["identifier"][0]["system"]
        self.system_value = imms["identifier"][0]["value"]
        self.patient_sk = f"{self.vaccine_type}#{imms_id}"
        self.identifier = f"{self.system_id}#{self.system_value}"


class ImmunizationRepository:
    def __init__(self, table: Table):
        self.table = table

    def get_immunization_by_identifier(
        self, identifier_pk: str, imms_vax_type_perms: list[str]
    ) -> Optional[dict]:
        response = self.table.query(
            IndexName="IdentifierGSI", KeyConditionExpression=Key("IdentifierPK").eq(identifier_pk)
        )
        if "Items" in response and len(response["Items"]) > 0:
            item = response["Items"][0]
            resp = dict()
            vaccine_type = self._vaccine_type(item["PatientSK"])
            if not validate_permissions(imms_vax_type_perms,ApiOperationCode.SEARCH, [vaccine_type]):
                raise UnauthorizedVaxError()
            resource = json.loads(item["Resource"])
            resp["id"] = resource.get("id")
            resp["version"] = int(response["Items"][0]["Version"])
            return resp
        else:
            return None

    def get_immunization_by_id(self, imms_id: str, imms_vax_type_perms: str) -> Optional[dict]:
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})
        item = response.get("Item")

        if not item:
            return None
        if item.get("DeletedAt") and item["DeletedAt"] != "reinstated":
            return None

        # Get vaccine type + validate permissions
        vaccine_type = self._vaccine_type(item["PatientSK"])
        if not validate_permissions(imms_vax_type_perms, ApiOperationCode.READ, [vaccine_type]):
            raise UnauthorizedVaxError()

        # Build response
        return {
            "Resource": json.loads(item["Resource"]),
            "Version": item["Version"]
        }

    def get_immunization_by_id_all(self, imms_id: str, imms: dict) -> Optional[dict]:
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})
        if "Item" in response:
            diagnostics = check_identifier_system_value(response, imms)
            if diagnostics:
                return diagnostics

            else:
                resp = dict()
                if "DeletedAt" in response["Item"]:
                    if response["Item"]["DeletedAt"] != "reinstated":
                        resp["Resource"] = json.loads(response["Item"]["Resource"])
                        resp["Version"] = response["Item"]["Version"]
                        resp["DeletedAt"] = True
                        resp["VaccineType"] = self._vaccine_type(response["Item"]["PatientSK"])
                        return resp
                    else:
                        resp["Resource"] = json.loads(response["Item"]["Resource"])
                        resp["Version"] = response["Item"]["Version"]
                        resp["DeletedAt"] = False
                        resp["Reinstated"] = True
                        resp["VaccineType"] = self._vaccine_type(response["Item"]["PatientSK"])
                        return resp
                else:
                    resp["Resource"] = json.loads(response["Item"]["Resource"])
                    resp["Version"] = response["Item"]["Version"]
                    resp["DeletedAt"] = False
                    resp["Reinstated"] = False
                    resp["VaccineType"] = self._vaccine_type(response["Item"]["PatientSK"])
                    return resp
        else:
            return None

    def create_immunization(
        self, immunization: dict, patient: any, imms_vax_type_perms, supplier_system
    ) -> dict:
        new_id = str(uuid.uuid4())
        immunization["id"] = new_id
        attr = RecordAttributes(immunization, patient)
        if not validate_permissions(imms_vax_type_perms,ApiOperationCode.CREATE, [attr.vaccine_type]):
            raise UnauthorizedVaxError()
        query_response = _query_identifier(self.table, "IdentifierGSI", "IdentifierPK", attr.identifier)

        if query_response is not None:
            raise IdentifierDuplicationError(identifier=attr.identifier)

        response = self.table.put_item(
            Item={
                "PK": attr.pk,
                "PatientPK": attr.patient_pk,
                "PatientSK": attr.patient_sk,
                "Resource": json.dumps(attr.resource, use_decimal=True),
                "IdentifierPK": attr.identifier,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": supplier_system,
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return immunization
        else:
            raise UnhandledResponseError(message="Non-200 response from dynamodb", response=response)

    def update_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: any,
        existing_resource_version: int,
        imms_vax_type_perms: list[str],
        supplier_system: str,
    ) -> tuple[dict, int]:
        attr = RecordAttributes(immunization, patient)
        self._handle_permissions(imms_vax_type_perms, attr)
        update_exp = self._build_update_expression(is_reinstate=False)

        self._check_duplicate_identifier(attr)

        return self._perform_dynamo_update(
            imms_id,
            update_exp,
            attr,
            existing_resource_version,
            supplier_system,
            deleted_at_required=False,
            update_reinstated=False,
        )

    def reinstate_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: any,
        existing_resource_version: int,
        imms_vax_type_perms: list[str],
        supplier_system: str,

    ) -> tuple[dict, int]:
        attr = RecordAttributes(immunization, patient)
        self._handle_permissions(imms_vax_type_perms, attr)
        update_exp = self._build_update_expression(is_reinstate=True)

        self._check_duplicate_identifier(attr)

        return self._perform_dynamo_update(
            imms_id,
            update_exp,
            attr,
            existing_resource_version,
            supplier_system,
            deleted_at_required=True,
            update_reinstated=False,
        )

    def update_reinstated_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: any,
        existing_resource_version: int,
        imms_vax_type_perms: list[str],
        supplier_system: str,
    ) -> tuple[dict, int]:
        attr = RecordAttributes(immunization, patient)
        self._handle_permissions(imms_vax_type_perms, attr)
        update_exp = self._build_update_expression(is_reinstate=False)

        self._check_duplicate_identifier(attr)

        return self._perform_dynamo_update(
            imms_id,
            update_exp,
            attr,
            existing_resource_version,
            supplier_system,
            deleted_at_required=True,
            update_reinstated=True,
        )

    def _handle_permissions(self, imms_vax_type_perms: list[str], attr: RecordAttributes):
        validate_permissions(imms_vax_type_perms, ApiOperationCode.UPDATE, [attr.vaccine_type])

    def _build_update_expression(self, is_reinstate: bool) -> str:
        if is_reinstate:
            return (
                "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
                "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, "
                "Operation = :operation, Version = :version, DeletedAt = :respawn, SupplierSystem = :supplier_system "
            )
        else:
            return (
                "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
                "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, "
                "Operation = :operation, Version = :version, SupplierSystem = :supplier_system "
            )

    def _check_duplicate_identifier(self, attr: RecordAttributes) -> dict:
        queryresponse = _query_identifier(self.table, "IdentifierGSI", "IdentifierPK", attr.identifier)
        if queryresponse is not None:
            items = queryresponse.get("Items", [])
            resource_dict = json.loads(items[0]["Resource"])
            if resource_dict["id"] != attr.resource["id"]:
                raise IdentifierDuplicationError(identifier=attr.identifier)
        return queryresponse

    def _perform_dynamo_update(
        self,
        imms_id: str,
        update_exp: str,
        attr: RecordAttributes,
        existing_resource_version: int,
        supplier_system: str,
        deleted_at_required: bool,
        update_reinstated: bool,
    ) -> Tuple[dict, int]:
        try:
            updated_version = existing_resource_version + 1
            condition_expression = Attr("PK").eq(attr.pk) & (
                Attr("DeletedAt").exists()
                if deleted_at_required
                else Attr("PK").eq(attr.pk) & Attr("DeletedAt").not_exists()
            )
            if deleted_at_required and update_reinstated == False:
                ExpressionAttributeValues = {
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, use_decimal=True),
                    ":operation": "UPDATE",
                    ":version": updated_version,
                    ":supplier_system": supplier_system,
                    ":respawn": "reinstated",
                }
            else:
                ExpressionAttributeValues = {
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, use_decimal=True),
                    ":operation": "UPDATE",
                    ":version": updated_version,
                    ":supplier_system": supplier_system,
                }

            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues=ExpressionAttributeValues,
                ReturnValues="ALL_NEW",
                ConditionExpression=condition_expression,
            )
            return self._handle_dynamo_response(response), updated_version
        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    def delete_immunization(
            self, imms_id: str, imms_vax_type_perms: str, supplier_system: str) -> dict:
        now_timestamp = int(time.time())

        try:
            item = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)}).get("Item")
            if not item:
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

            if not item.get("DeletedAt") or item.get("DeletedAt") == "reinstated":
                vaccine_type = self._vaccine_type(item["PatientSK"])
                if not validate_permissions(imms_vax_type_perms, ApiOperationCode.DELETE, [vaccine_type]):
                    raise UnauthorizedVaxError()

            # Proceed with delete update
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=(
                    "SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system"
                ),
                ExpressionAttributeValues={
                    ":timestamp": now_timestamp,
                    ":operation": "DELETE",
                    ":supplier_system": supplier_system,
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=(
                    Attr("PK").eq(_make_immunization_pk(imms_id)) &
                    (Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated"))
                ),
            )

            return self._handle_dynamo_response(response)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

def find_immunizations(self, patient_identifier: str, vaccine_types: list):
    """it should find all of the specified patient's Immunization events for all of the specified vaccine_types"""
    
    # ✅ Add debug logging
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("SAW fi...1: find_immunizations called with patient_identifier: '%s', vaccine_types: %s", 
                patient_identifier, vaccine_types)
    
    # Create the patient PK and log it
    patient_pk = _make_patient_pk(patient_identifier)
    logger.info("SAW fi...2: patient_pk created: '%s'", patient_pk)

    condition = Key("PatientPK").eq(patient_pk)
    is_not_deleted = Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")

    logger.info("SAW fi...3: executing DynamoDB query on PatientGSI index")

    response = self.table.query(
        IndexName="PatientGSI",
        KeyConditionExpression=condition,
        FilterExpression=is_not_deleted,
    )
    
    # ✅ Log the raw DynamoDB response
    logger.info("SAW fi...4: DynamoDB query response - Count: %s, ScannedCount: %s", 
                response.get("Count", 0), response.get("ScannedCount", 0))
    
    if "Items" in response:
        raw_items = response["Items"]
        logger.info("SAW fi...5: total items returned from DynamoDB: %d", len(raw_items))
        
        # Log first few items for debugging
        if raw_items:
            logger.info("SAW fi...6: sample raw item keys: %s", list(raw_items[0].keys()))
            logger.info("SAW fi...7: first few PatientSK values: %s",
                       [item.get("PatientSK", "MISSING") for item in raw_items[:3]])
        
        # Filter the response to contain only the requested vaccine types
        items = [x for x in raw_items if x["PatientSK"].split("#")[0] in vaccine_types]

        logger.info("SAW fi...8: after vaccine_types filtering (%s): %d items", vaccine_types, len(items))

        if items:
            # Log the vaccine types found
            found_vaccine_types = [item["PatientSK"].split("#")[0] for item in items]
            logger.info("SAW fi...9: found vaccine types: %s", found_vaccine_types)
        else:
            # Debug why no items matched
            all_vaccine_types = [item["PatientSK"].split("#")[0] for item in raw_items]
            logger.warning("SAW fi...10: no items matched vaccine_types filter!")
            logger.warning("SAW fi...11: requested vaccine_types: %s", vaccine_types)
            logger.warning("SAW fi...12: available vaccine_types in data: %s", list(set(all_vaccine_types)))

        # Return a list of the FHIR immunization resource JSON items
        final_resources = [json.loads(item["Resource"]) for item in items]
        logger.info("SAW fi...13: returning %d FHIR resources", len(final_resources))

        return final_resources
    else:
        logger.error("SAW fi...14: No 'Items' key in DynamoDB response!")
        logger.error("SAW fi...15: Response keys: %s", list(response.keys()))
        raise UnhandledResponseError(message=f"Unhandled error. Query failed", response=response)

    @staticmethod
    def _handle_dynamo_response(response):
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return json.loads(response["Attributes"]["Resource"])
        else:
            raise UnhandledResponseError(message="Non-200 response from dynamodb", response=response)

    @staticmethod
    def _vaccine_type(patientsk) -> str:
        parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
        return parsed[0]
