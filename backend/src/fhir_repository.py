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
from mappings import vaccination_procedure_snomed_codes
from models.errors import ResourceNotFoundError, UnhandledResponseError, IdentifierDuplicationError
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

from models.utils.generic_utils import get_disease_type


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
            IndexName=index,
            KeyConditionExpression=Key(pk).eq(identifier),
            Limit=1
        )
    if queryResponse.get('Count', 0) > 0:
        return queryResponse


@dataclass
class RecordAttributes:
    pk: str
    patient_pk: str
    patient_sk: str
    resource: dict
    patient: dict
    disease_type: str
    timestamp: int
    identifier: str

    def __init__(self, imms: dict, patient: dict):
        """Create attributes that may be used in dynamodb table"""
        imms_id = imms["id"]
        self.pk = _make_immunization_pk(imms_id)
        self.patient_pk = _make_patient_pk(
            [x for x in imms["contained"] if x.get("resourceType") == "Patient"][0][
                "identifier"
            ][0]["value"]
        )
        self.patient = patient
        self.resource = imms
        self.timestamp = int(time.time())
        self.disease_type = get_disease_type(imms)

        self.patient_sk = f"{self.disease_type}#{imms_id}"
        self.identifier = imms['identifier'][0]['value']


class ImmunizationRepository:
    def __init__(self, table: Table):
        self.table = table

    def get_immunization_by_id(self, imms_id: str) -> Optional[dict]:
        response = self.table.get_item(Key={"PK": _make_immunization_pk(imms_id)})

        if "Item" in response:
            return (
                None
                if "DeletedAt" in response["Item"]
                else json.loads(response["Item"]["Resource"])
            )
        else:
            return None

    def create_immunization(self, immunization: dict, patient: dict) -> dict:
        new_id = str(uuid.uuid4())
        immunization["id"] = new_id
        attr = RecordAttributes(immunization, patient)

        query_response = _query_identifier(self.table, 'IdentifierGSI', 'IdentifierPK', attr.identifier)

        if query_response is not None and 'DeletedAt' not in query_response['Items'][0]:
                raise IdentifierDuplicationError(identifier=attr.identifier)

        response = self.table.put_item(Item={
            'PK': attr.pk,
            'PatientPK': attr.patient_pk,
            'PatientSK': attr.patient_sk,
            'Resource': json.dumps(attr.resource, cls=DecimalEncoder),
            'Patient': attr.patient,
            'IdentifierPK': attr.identifier
        })

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return immunization
        else:
            raise UnhandledResponseError(
                message="Non-200 response from dynamodb", response=response
            )

    def update_immunization(self, imms_id: str, immunization: dict, patient: dict) -> dict:
        attr = RecordAttributes(immunization, patient)
        # "Resource" is a dynamodb reserved word
        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, Patient = :patient"
        )

        queryResponse = _query_identifier(self.table, 'IdentifierGSI', 'IdentifierPK', attr.identifier)

        if queryResponse != None:
            items = queryResponse.get('Items', [])
            resource_dict = json.loads(items[0]['Resource'])
            if resource_dict['id'] != attr.resource['id'] and 'DeletedAt' not in items[0]:
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
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(attr.pk)& Attr("DeletedAt").not_exists()
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

    def delete_immunization(self, imms_id: str) -> dict:
        now_timestamp = int(time.time())
        try:
            response = self.table.update_item(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression="SET DeletedAt = :timestamp",
                ExpressionAttributeValues={
                    ":timestamp": now_timestamp,
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

    def find_immunizations(self, nhs_number: str):
        """it should find all patient's Immunization events for a specified disease_code"""
        condition = Key("PatientPK").eq(_make_patient_pk(nhs_number))
        is_not_deleted = Attr("DeletedAt").not_exists()

        response = self.table.query(
            IndexName="PatientGSI",
            KeyConditionExpression=condition,
            FilterExpression=is_not_deleted,
        )
        if "Items" in response:
            return [json.loads(item["Resource"]) for item in response["Items"]]
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