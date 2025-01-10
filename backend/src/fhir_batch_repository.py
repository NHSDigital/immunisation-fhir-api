import os
import uuid
import boto3
import time
import simplejson as json
from dataclasses import dataclass
import botocore.exceptions
from boto3.dynamodb.conditions import Key, Attr
from models.errors import UnhandledResponseError, IdentifierDuplicationError, ResourceNotFoundError, ResourceFoundError


def create_table(region_name="eu-west-2"):
    table_name = os.environ["DYNAMODB_TABLE_NAME"]
    dynamodb = boto3.resource("dynamodb", region_name=region_name)
    return dynamodb.Table(table_name)


def _make_immunization_pk(_id: str):
    return f"Immunization#{_id}"


def _make_patient_pk(_id: str):
    return f"Patient#{_id}"


def _query_identifier(table, index, pk, identifier, is_present):
    retries = 0
    delay_milliseconds = 60
    if is_present:
        while retries < 30:
            queryresponse = table.query(IndexName=index, KeyConditionExpression=Key(pk).eq(identifier), Limit=1)

            if queryresponse.get("Count", 0) > 0:
                return queryresponse

            if retries > 6:
                print(f"{identifier}: Crossed {retries} retries")

            retries += 1
            # Delay time in milliseconds
            time.sleep(delay_milliseconds / 1000)

        return None
    else:
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
    vaccine_type: str
    timestamp: int
    identifier: str
    supplier: str
    version: int

    def __init__(self, imms: dict, vax_type: str, supplier: str, version: int):
        """Create attributes that may be used in dynamodb table"""
        imms_id = imms["id"]
        self.pk = _make_immunization_pk(imms_id)
        nhs_number = get_nhs_number(imms)
        self.patient_pk = _make_patient_pk(nhs_number)
        self.resource = imms
        self.timestamp = int(time.time())
        self.vaccine_type = vax_type
        self.supplier = supplier
        self.version = version + 1
        self.system_id = imms["identifier"][0]["system"]
        self.system_value = imms["identifier"][0]["value"]
        self.patient_sk = f"{self.vaccine_type}#{imms_id}"
        self.identifier = f"{self.system_id}#{self.system_value}"


class ImmunizationBatchRepository:
    def __init__(self):
        pass

    def create_immunization(
        self, immunization: any, supplier_system: str, vax_type: str, table: any, is_present: bool
    ) -> dict:
        new_id = str(uuid.uuid4())
        immunization["id"] = new_id
        attr = RecordAttributes(immunization, vax_type, supplier_system, 0)

        query_response = _query_identifier(table, "IdentifierGSI", "IdentifierPK", attr.identifier, is_present)

        if query_response is not None:
            raise IdentifierDuplicationError(identifier=attr.identifier)

        try:
            response = table.put_item(
                Item={
                    "PK": attr.pk,
                    "PatientPK": attr.patient_pk,
                    "PatientSK": attr.patient_sk,
                    "Resource": json.dumps(attr.resource, use_decimal=True),
                    "IdentifierPK": attr.identifier,
                    "Operation": "CREATE",
                    "Version": attr.version,
                    "SupplierSystem": attr.supplier,
                },
                ConditionExpression=Attr("PK").ne(attr.pk),
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                return attr.pk
            else:
                raise UnhandledResponseError(message="Non-200 response from dynamodb", response=response)

        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceFoundError(resource_type="Immunization", resource_id=attr.pk)
            raise UnhandledResponseError(
                message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                response=error.response,
            )

    def update_immunization(
        self, immunization: any, supplier_system: str, vax_type: str, table: any, is_present: bool
    ) -> dict:
        identifier = self._identifier_response(immunization)
        query_response = _query_identifier(table, "IdentifierGSI", "IdentifierPK", identifier, is_present)
        if query_response is None:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=identifier)
        old_id, version = self._get_id_version(query_response)
        deleted_at_required, update_reinstated, is_reinstate = self._get_record_status(query_response)

        immunization["id"] = old_id.split("#")[1]
        attr = RecordAttributes(immunization, vax_type, supplier_system, version)

        update_exp = self._build_update_expression(is_reinstate=is_reinstate)

        return self._perform_dynamo_update(
            update_exp,
            attr,
            deleted_at_required=deleted_at_required,
            update_reinstated=update_reinstated,
            table=table,
        )

    def delete_immunization(
        self, immunization: any, supplier_system: str, vax_type: str, table: any, is_present: bool
    ) -> dict:
        identifier = self._identifier_response(immunization)
        query_response = _query_identifier(table, "IdentifierGSI", "IdentifierPK", identifier, is_present)
        if query_response is None:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=identifier)
        try:
            now_timestamp = int(time.time())
            imms_id = self._get_pk(query_response)
            response = table.update_item(
                Key={"PK": imms_id},
                UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
                ExpressionAttributeValues={
                    ":timestamp": now_timestamp,
                    ":operation": "DELETE",
                    ":supplier_system": supplier_system,
                },
                ReturnValues="ALL_NEW",
                ConditionExpression=Attr("PK").eq(imms_id)
                & (Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")),
            )
            return self._handle_dynamo_response(response, imms_id)

        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )

    @staticmethod
    def _handle_dynamo_response(response, imms_id):
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return imms_id
        else:
            raise UnhandledResponseError(message="Non-200 response from dynamodb", response=response)

    @staticmethod
    def _identifier_response(immunization: any):
        system_id = immunization["identifier"][0]["system"]
        system_value = immunization["identifier"][0]["value"]
        return f"{system_id}#{system_value}"

    @staticmethod
    def _get_pk(query_response: any):
        if query_response.get("Count") == 1:
            return query_response["Items"][0]["PK"]

    @staticmethod
    def _get_id_version(query_response: any):
        if query_response.get("Count") == 1:
            old_id = query_response["Items"][0]["PK"]
            version = query_response["Items"][0]["Version"]
            return old_id, version

    @staticmethod
    def _get_record_status(query_response: any):
        deleted_at_required = False
        update_reinstated = False
        is_reinstate = False
        if query_response.get("Count") == 1:
            if "DeletedAt" in query_response["Items"][0]:
                deleted_at_required = True
                is_reinstate = True
                if query_response["Items"][0]["DeletedAt"] == "reinstated":
                    update_reinstated = True
                    is_reinstate = False

        return deleted_at_required, update_reinstated, is_reinstate

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

    def _perform_dynamo_update(
        self,
        update_exp: str,
        attr: RecordAttributes,
        deleted_at_required: bool,
        update_reinstated: bool,
        table: any,
    ) -> dict:
        try:
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
                    ":version": attr.version,
                    ":supplier_system": attr.supplier,
                    ":respawn": "reinstated",
                }
            else:
                ExpressionAttributeValues = {
                    ":timestamp": attr.timestamp,
                    ":patient_pk": attr.patient_pk,
                    ":patient_sk": attr.patient_sk,
                    ":imms_resource_val": json.dumps(attr.resource, use_decimal=True),
                    ":operation": "UPDATE",
                    ":version": attr.version,
                    ":supplier_system": attr.supplier,
                }

            response = table.update_item(
                Key={"PK": attr.pk},
                UpdateExpression=update_exp,
                ExpressionAttributeNames={
                    "#imms_resource": "Resource",
                },
                ExpressionAttributeValues=ExpressionAttributeValues,
                ReturnValues="ALL_NEW",
                ConditionExpression=condition_expression,
            )
            return self._handle_dynamo_response(response, attr.pk)
        except botocore.exceptions.ClientError as error:
            # Either resource didn't exist or it has already been deleted. See ConditionExpression in the request
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ResourceNotFoundError(resource_type="Immunization", resource_id=attr.pk)
            else:
                raise UnhandledResponseError(
                    message=f"Unhandled error from dynamodb: {error.response['Error']['Code']}",
                    response=error.response,
                )
