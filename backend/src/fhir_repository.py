import json
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    IdentifierDuplicationError,
    UnauthorizedVaxError
)
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

from models.utils.validation_utils import get_vaccine_type


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        # if passed in object is instance of Decimal
        # convert it to a string
        if isinstance(o, Decimal):
            return float(o)
        # otherwise use the default behavior
        return json.JSONEncoder.default(self, o)


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
    queryResponse = table.query(
        IndexName=index, KeyConditionExpression=Key(pk).eq(identifier), Limit=1
    )
    if queryResponse.get("Count", 0) > 0:
        return queryResponse


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

    def __init__(self, imms: dict, patient: dict):
        """Create attributes that may be used in dynamodb table"""
        imms_id = imms["id"]
        self.pk = _make_immunization_pk(imms_id)
        if patient:
            nhs_number = [
                x for x in imms["contained"] if x.get("resourceType") == "Patient"
            ][0]["identifier"][0]["value"]
        else:
            nhs_number = "TBC"
        self.patient_pk = _make_patient_pk(nhs_number)
        self.patient = patient
        self.resource = imms
        self.timestamp = int(time.time())
        self.vaccine_type = get_vaccine_type(imms)

        self.patient_sk = f"{self.vaccine_type}#{imms_id}"
        self.identifier = imms["identifier"][0]["value"]


class ImmunizationRepository:
    def __init__(self, table: Table):
        self.table = table


    def get_immunization_by_identifier(self, identifier_pk: str, imms_vax_type_perms: str) -> Optional[dict]:
        print(f"identifier_pk:{identifier_pk}")
        response = self.table.scan(
            FilterExpression=Attr('IdentifierPK').eq(identifier_pk)
        )
        print(f"response:{response}")
        if "Items" in response and len(response["Items"]) > 0:
            item = response["Items"][0]
            resp = dict()
            vaccine_type = self._vaccine_type(item["PatientSK"])
            vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
            vax_type_perm= self._vaccine_permission(vaccine_type, "read")
            self._check_permission(vax_type_perm,vax_type_perms)
            resource = json.loads(item["Resource"])
            resp["id"] = resource.get('id')
            return resp
        else:
            return None
  

    def get_immunization_by_id(self, imms_id: str, imms_vax_type_perms: str) -> Optional[dict]:
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})
        print(f"responsedb:{response}")
        if "Item" in response:
            if "DeletedAt" in response["Item"]:
                return None
            else:
                resp = dict()
                vaccine_type = self._vaccine_type(response["Item"]["PatientSK"])
                vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
                vax_type_perm= self._vaccine_permission(vaccine_type, "read")
                self._check_permission(vax_type_perm,vax_type_perms)
                resp["Resource"] = json.loads(response["Item"]["Resource"])
                resp["Version"] = response["Item"]["Version"]
                return resp
        else:
            return None

    def get_immunization_by_id_all(self, imms_id: str) -> Optional[dict]:
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})

        if "Item" in response:
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

    def create_immunization(self, immunization: dict, patient: dict , imms_vax_type_perms) -> dict:
        new_id = str(uuid.uuid4())
        immunization["id"] = new_id
        attr = RecordAttributes(immunization, patient)
        vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
        vax_type_perm= self._vaccine_permission(attr.vaccine_type, "create")
        self._check_permission(vax_type_perm,vax_type_perms)
        query_response = _query_identifier(
            self.table, "IdentifierGSI", "IdentifierPK", attr.identifier
        )

        if query_response is not None and "DeletedAt" not in query_response["Items"][0]:
            raise IdentifierDuplicationError(identifier=attr.identifier)

        response = self.table.put_item(
            Item={
                "PK": attr.pk,
                "PatientPK": attr.patient_pk,
                "PatientSK": attr.patient_sk,
                "Resource": json.dumps(attr.resource, cls=DecimalEncoder),
                "Patient": attr.patient,
                "IdentifierPK": attr.identifier,
                "Operation": "CREATE",
                "Version": 1,
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return immunization
        else:
            raise UnhandledResponseError(
                message="Non-200 response from dynamodb", response=response
            )

    def update_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: dict,
        existing_resource_version: int,
        imms_vax_type_perms: str
    ) -> dict:
        attr = RecordAttributes(immunization, patient)
        vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
        vax_type_perm= self._vaccine_permission(attr.vaccine_type, "update")
        self._check_permission(vax_type_perm,vax_type_perms)
        # "Resource" is a dynamodb reserved word
        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, Patient = :patient, "
            "Operation = :operation, Version = :version "
        )

        queryResponse = _query_identifier(
            self.table, "IdentifierGSI", "IdentifierPK", attr.identifier
        )

        if queryResponse != None:
            items = queryResponse.get("Items", [])
            resource_dict = json.loads(items[0]["Resource"])
            if resource_dict["id"] != attr.resource["id"]:
                raise IdentifierDuplicationError(identifier=attr.identifier)

        try:
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues={
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, cls=DecimalEncoder),
                    ":patient": attr.patient,
                    ":operation": "UPDATE",
                    ":version": existing_resource_version + 1,
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(attr.pk)
                & Attr("DeletedAt").not_exists(),
            )
            return self._handle_dynamo_response(response)

        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(
                    resource_type="Immunization", resource_id=imms_id
                )
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    def reinstate_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: dict,
        existing_resource_version: int,
        imms_vax_type_perms: str
    ) -> dict:
        attr = RecordAttributes(immunization, patient)
        vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
        vax_type_perm= self._vaccine_permission(attr.vaccine_type, "update")
        self._check_permission(vax_type_perm,vax_type_perms)
        # "Resource" is a dynamodb reserved word
        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, Patient = :patient, "
            "Operation = :operation, Version = :version, DeletedAt = :respawn "
        )

        queryResponse = _query_identifier(
            self.table, "IdentifierGSI", "IdentifierPK", attr.identifier
        )

        if queryResponse != None:
            items = queryResponse.get("Items", [])
            resource_dict = json.loads(items[0]["Resource"])
            if resource_dict["id"] != attr.resource["id"]:
                raise IdentifierDuplicationError(identifier=attr.identifier)

        try:
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues={
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, cls=DecimalEncoder),
                    ":patient": attr.patient,
                    ":operation": "UPDATE",
                    ":version": existing_resource_version + 1,
                    ":respawn": "reinstated",
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(attr.pk) & Attr("DeletedAt").exists(),
            )
            return self._handle_dynamo_response(response)

        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(
                    resource_type="Immunization", resource_id=imms_id
                )
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    def update_reinstated_immunization(
        self,
        imms_id: str,
        immunization: dict,
        patient: dict,
        existing_resource_version: int,
        imms_vax_type_perms: str
    ) -> dict:
        attr = RecordAttributes(immunization, patient)
        vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
        vax_type_perm= self._vaccine_permission(attr.vaccine_type, "update")
        self._check_permission(vax_type_perm,vax_type_perms)
        # "Resource" is a dynamodb reserved word
        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, Patient = :patient, "
            "Operation = :operation, Version = :version "
        )

        queryResponse = _query_identifier(
            self.table, "IdentifierGSI", "IdentifierPK", attr.identifier
        )

        if queryResponse != None:
            items = queryResponse.get("Items", [])
            resource_dict = json.loads(items[0]["Resource"])
            if resource_dict["id"] != attr.resource["id"]:
                raise IdentifierDuplicationError(identifier=attr.identifier)

        try:
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues={
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, cls=DecimalEncoder),
                    ":patient": attr.patient,
                    ":operation": "UPDATE",
                    ":version": existing_resource_version + 1,
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(attr.pk) & Attr("DeletedAt").exists(),
            )
            return self._handle_dynamo_response(response)

        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(
                    resource_type="Immunization", resource_id=imms_id
                )
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    def delete_immunization(self, imms_id: str, imms_vax_type_perms: str) -> dict:
        now_timestamp = int(time.time())
        try:
            resp = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})

            if "Item" in resp:
                if not "DeletedAt" in resp["Item"]:
                    vaccine_type = self._vaccine_type(resp["Item"]["PatientSK"])
                    vax_type_perms = self._parse_vaccine_permissions(imms_vax_type_perms)
                    vax_type_perm= self._vaccine_permission(vaccine_type, "delete")
                    self._check_permission(vax_type_perm,vax_type_perms)
                    
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation",
                ExpressionAttributeValues={
                    ":timestamp": now_timestamp,
                    ":operation": "DELETE",
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(_make_immunization_pk(imms_id))
                & Attr("DeletedAt").not_exists(),
            )
            return self._handle_dynamo_response(response)

        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(
                    resource_type="Immunization", resource_id=imms_id
                )
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    def find_immunizations(self, patient_identifier: str, vaccine_types: list):
        """it should find all of the specified patient's Immunization events for all of the specified vaccine_types"""
        condition = Key("PatientPK").eq(_make_patient_pk(patient_identifier))
        is_not_deleted = Attr("DeletedAt").not_exists()

        response = self.table.query(
            IndexName="PatientGSI",
            KeyConditionExpression=condition,
            FilterExpression=is_not_deleted,
        )

        if "Items" in response:
            # Filter the response to contain only the requested vaccine types
            items = [x for x in response["Items"] if x["PatientSK"].split("#")[0] in vaccine_types]

            # Return a list of the FHIR immunization resource JSON items
            return [json.loads(item["Resource"]) for item in items]
        else:
            raise UnhandledResponseError(
                message=f"Unhandled error. Query failed", response=response
            )

    @staticmethod
    def _handle_dynamo_response(response):
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return json.loads(response["Attributes"]["Resource"])
        else:
            raise UnhandledResponseError(
                message="Non-200 response from dynamodb", response=response
            )
            
    @staticmethod
    def _vaccine_permission( vaccine_type, operation) -> set:
        vaccine_permission = set()
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
            raise UnauthorizedVaxError()
        else:
            return None
        
    @staticmethod
    def _vaccine_type( patientsk ) -> str:
        parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
        return parsed[0]