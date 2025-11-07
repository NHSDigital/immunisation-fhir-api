import os
import time
from dataclasses import dataclass
from typing import Optional

import boto3
import botocore.exceptions
import simplejson as json
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config
from fhir.resources.R4B.fhirtypes import Id
from fhir.resources.R4B.immunization import Immunization
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from responses import logger

from common.models.api_errors import UnhandledResponseError
from common.models.errors import ResourceNotFoundError
from common.models.constants import Constants
from common.models.immunization_record_metadata import ImmunizationRecordMetadata
from common.models.utils.generic_utils import get_contained_patient
from common.models.utils.validation_utils import (
    get_vaccine_type,
)


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

    def get_immunization_by_identifier(self, identifier_pk: str) -> tuple[Optional[dict], Optional[str]]:
        response = self.table.query(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(identifier_pk),
        )

        if "Items" in response and len(response["Items"]) > 0:
            item = response["Items"][0]
            vaccine_type = self._vaccine_type(item["PatientSK"])
            resource = json.loads(item["Resource"])
            version = int(response["Items"][0]["Version"])
            return {
                "resource": resource,
                "id": resource.get("id"),
                "version": version,
            }, vaccine_type
        else:
            return None, None

    def get_immunization_and_resource_meta_by_id(
        self, imms_id: str, include_deleted: bool = False
    ) -> tuple[Optional[dict], Optional[ImmunizationRecordMetadata]]:
        """Retrieves the immunization and resource metadata from the VEDS table"""
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})
        item = response.get("Item")

        if not item:
            return None, None

        deleted_at_attr = item.get("DeletedAt")

        is_deleted = deleted_at_attr is not None and deleted_at_attr != Constants.REINSTATED_RECORD_STATUS
        is_reinstated = deleted_at_attr == Constants.REINSTATED_RECORD_STATUS

        if is_deleted and not include_deleted:
            return None, None

        imms_record_meta = ImmunizationRecordMetadata(int(item.get("Version")), is_deleted, is_reinstated)

        return json.loads(item.get("Resource", {})), imms_record_meta

    def check_immunization_identifier_exists(self, system: str, unique_id: str) -> bool:
        """Checks whether an immunization with the given immunization identifier (system + local ID) exists."""
        response = self.table.query(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(f"{system}#{unique_id}"),
        )

        if "Items" in response and len(response["Items"]) > 0:
            return True

        return False

    def create_immunization(self, immunization: Immunization, supplier_system: str) -> Id:
        """Creates a new immunization record returning the unique id if successful."""
        immunization_as_dict = immunization.dict()

        patient = get_contained_patient(immunization_as_dict)
        attr = RecordAttributes(immunization_as_dict, patient)

        response = self.table.put_item(
            Item={
                "PK": attr.pk,
                "PatientPK": attr.patient_pk,
                "PatientSK": attr.patient_sk,
                "Resource": immunization.json(use_decimal=True),
                "IdentifierPK": attr.identifier,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": supplier_system,
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise UnhandledResponseError(message="Non-200 response from dynamodb", response=dict(response))

        return immunization.id

    def update_immunization(
        self,
        imms_id: str,
        immunization: dict,
        existing_record_meta: ImmunizationRecordMetadata,
        supplier_system: str,
    ) -> int:
        # VED-898 - consider refactoring to pass FHIR Immunization object rather than dict between Service -> Repository
        patient = get_contained_patient(immunization)
        attr = RecordAttributes(immunization, patient)
        reinstate_operation_required = existing_record_meta.is_deleted

        update_exp = self._build_update_expression(is_reinstate=reinstate_operation_required)

        return self._perform_dynamo_update(
            imms_id,
            update_exp,
            attr,
            existing_record_meta.resource_version,
            supplier_system,
            reinstate_operation_required=reinstate_operation_required,
            record_contains_deletion_history=(reinstate_operation_required or existing_record_meta.is_reinstated),
        )

    @staticmethod
    def _build_update_expression(is_reinstate: bool) -> str:
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

    def _perform_dynamo_update(
        self,
        imms_id: str,
        update_exp: str,
        attr: RecordAttributes,
        existing_resource_version: int,
        supplier_system: str,
        reinstate_operation_required: bool,
        record_contains_deletion_history: bool,
    ) -> int:
        updated_version = existing_resource_version + 1
        condition_expression = Attr("PK").eq(attr.pk) & (
            Attr("DeletedAt").exists()
            if record_contains_deletion_history
            else Attr("PK").eq(attr.pk) & Attr("DeletedAt").not_exists()
        )

        expression_attribute_values = {
            ":timestamp": attr.timestamp,
            ":patient_pk": attr.patient_pk,
            ":patient_sk": attr.patient_sk,
            ":imms_resource_val": json.dumps(attr.resource, use_decimal=True),
            ":operation": "UPDATE",
            ":version": updated_version,
            ":supplier_system": supplier_system,
        }
        if reinstate_operation_required:
            expression_attribute_values.update(
                {
                    ":respawn": "reinstated",
                }
            )

        try:
            self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=condition_expression,
            )
        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

            raise error

        return updated_version

    def delete_immunization(self, imms_id: str, supplier_system: str) -> None:
        now_timestamp = int(time.time())

        try:
            self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=(
                    "SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system"
                ),
                ExpressionAttributeValues={
                    ":timestamp": now_timestamp,
                    ":operation": "DELETE",
                    ":supplier_system": supplier_system,
                },
                ConditionExpression=(
                    Attr("PK").eq(_make_immunization_pk(imms_id))
                    & (Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated"))
                ),
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)
            else:
                raise error

    def find_immunizations(self, patient_identifier: str, vaccine_types: set):
        """it should find all of the specified patient's Immunization events for all of the specified vaccine_types"""
        condition = Key("PatientPK").eq(_make_patient_pk(patient_identifier))
        is_not_deleted = Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")

        raw_items = self.get_all_items(condition, is_not_deleted)

        if raw_items:
            # Filter the response to contain only the requested vaccine types
            items = [x for x in raw_items if x["PatientSK"].split("#")[0] in vaccine_types]

            # Return a list of the FHIR immunization resource JSON items
            final_resources = [
                {
                    **json.loads(item["Resource"]),
                    "meta": {"versionId": int(item.get("Version", 1))},
                }
                for item in items
            ]

            return final_resources
        else:
            logger.warning("no items matched patient_identifier filter!")
            return []

    def get_all_items(self, condition, is_not_deleted):
        """Query DynamoDB and paginate through all results."""
        all_items = []
        last_evaluated_key = None

        while True:
            query_args = {
                "IndexName": "PatientGSI",
                "KeyConditionExpression": condition,
                "FilterExpression": is_not_deleted,
            }
            if last_evaluated_key:
                query_args["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_args)
            if "Items" not in response:
                raise UnhandledResponseError(message="No Items in DynamoDB response", response=response)

            items = response.get("Items", [])
            all_items.extend(items)

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return all_items

    @staticmethod
    def _vaccine_type(patientsk) -> str:
        parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
        return parsed[0]
