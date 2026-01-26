import os
import unittest
from copy import deepcopy
from unittest.mock import ANY, MagicMock, Mock, patch
from uuid import uuid4

import boto3
import botocore.exceptions
import simplejson as json
from moto import mock_aws

from common.models.errors import (
    IdentifierDuplicationError,
    ResourceFoundError,
    ResourceNotFoundError,
    UnhandledResponseError,
)
from repository.fhir_batch_repository import ImmunizationBatchRepository, create_table
from test_common.testing_utils.immunization_utils import create_covid_immunization_dict

imms_id = str(uuid4())


def _make_immunization_pk(_id):
    return f"Immunization#{_id}"


@mock_aws
class TestImmunizationBatchRepository(unittest.TestCase):
    def setUp(self):
        os.environ["DYNAMODB_TABLE_NAME"] = "test-immunization-table"
        self.dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        self.table = MagicMock()
        self.table.wait_until_exists()
        self.repository = ImmunizationBatchRepository()
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})
        self.table.get_item = MagicMock(return_value=None)
        self.immunization = create_covid_immunization_dict(imms_id)
        self.table.update_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("common.models.utils.validation_utils.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()


class TestCreateImmunization(TestImmunizationBatchRepository):
    def modify_immunization(self, remove_nhs):
        """Modify the immunization object by removing NHS number if required"""
        if remove_nhs:
            for i, x in enumerate(self.immunization["contained"]):
                if x["resourceType"] == "Patient":
                    del self.immunization["contained"][i]
                    break

    def create_immunization_test_logic(self, last_imms_pk, remove_nhs):
        """Common logic for testing immunization creation."""
        self.mock_redis.hget.side_effect = ["COVID"]
        self.mock_redis_getter.return_value = self.mock_redis
        self.modify_immunization(remove_nhs)

        self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, last_imms_pk)
        item = self.table.put_item.call_args.kwargs["Item"]

        self.table.put_item.assert_called_with(
            Item={
                "PK": ANY,
                "PatientPK": ANY,
                "PatientSK": ANY,
                "Resource": json.dumps(self.immunization, use_decimal=True),
                "IdentifierPK": ANY,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": "supplier",
            },
            ConditionExpression=ANY,
        )
        self.assertEqual(item["PK"], f"Immunization#{self.immunization['id']}")

    def test_create_immunization_with_nhs_number(self):
        """Test creating Immunization with NHS number."""
        self.create_immunization_test_logic(last_imms_pk=None, remove_nhs=False)

    def test_create_immunization_without_nhs_number(self):
        """Test creating Immunization without NHS number."""

        self.create_immunization_test_logic(last_imms_pk=None, remove_nhs=True)

    def test_create_immunization_duplicate(self):
        """it should not create Immunization since the request is duplicate"""
        self.table.query = MagicMock(
            return_value={
                "id": imms_id,
                "identifier": [{"system": "test-system", "value": "12345"}],
                "contained": [{"resourceType": "Patient", "identifier": [{"value": "98765"}]}],
                "Count": 1,
            }
        )
        with self.assertRaises(IdentifierDuplicationError):
            self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.table.put_item.assert_not_called()

    def test_create_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.put_item = MagicMock(return_value=response)
        with self.assertRaises(UnhandledResponseError) as e:
            self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_create_immunization_unhandled_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        response = {"Error": {"Code": "InternalServerError"}}
        with unittest.mock.patch.object(
            self.table,
            "put_item",
            side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem"),
        ):
            with self.assertRaises(UnhandledResponseError) as e:
                self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_create_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(
            self.table,
            "put_item",
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
            ),
        ):
            with self.assertRaises(ResourceFoundError):
                self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)


class TestUpdateImmunization(TestImmunizationBatchRepository):
    def test_update_immunization(self):
        """it should update Immunization record"""

        test_item = {
            "PK": _make_immunization_pk(imms_id),
            "Resource": json.dumps(self.immunization),
            "Version": 1,
        }
        test_item_deleted = deepcopy(test_item)
        test_item_deleted["DeletedAt"] = "20210101"

        test_item_reinstated = deepcopy(test_item)
        test_item_reinstated["DeletedAt"] = "reinstated"

        test_cases = [
            # Update scenario
            {
                "get_item_response": {
                    "Item": test_item,
                },
                "query_response": {
                    "Count": 1,
                    "Items": [test_item],
                },
                "expected_extra_values": {},  # No extra assertion values
            },
            # Reinstated scenario
            {
                "get_item_response": {
                    "Item": test_item_deleted,
                },
                "query_response": {
                    "Count": 1,
                    "Items": [test_item_deleted],
                },
                "expected_extra_values": {":respawn": "reinstated"},
            },
            # Update reinstated scenario
            {
                "get_item_response": {
                    "Item": test_item_reinstated,
                },
                "query_response": {
                    "Count": 1,
                    "Items": [test_item_reinstated],
                },
                "expected_extra_values": {},
            },
        ]
        for last_imms_pk in [_make_immunization_pk(imms_id), None]:
            for case in test_cases:
                with self.subTest(last_imms_pk=last_imms_pk, case=case):
                    if last_imms_pk:
                        self.table.get_item = MagicMock(return_value=case["get_item_response"])
                    else:
                        self.table.query = MagicMock(return_value=case["query_response"])
                    response = self.repository.update_immunization(
                        self.immunization,
                        "supplier",
                        "vax-type",
                        self.table,
                        last_imms_pk,
                    )
                    expected_values = {
                        ":timestamp": ANY,
                        ":patient_pk": ANY,
                        ":patient_sk": ANY,
                        ":imms_resource_val": json.dumps(self.immunization),
                        ":operation": "UPDATE",
                        ":version": 2,
                        ":supplier_system": "supplier",
                    }
                    expected_values.update(case["expected_extra_values"])

                    self.table.update_item.assert_called_with(
                        Key={"PK": _make_immunization_pk(imms_id)},
                        UpdateExpression=ANY,
                        ExpressionAttributeNames={"#imms_resource": "Resource"},
                        ExpressionAttributeValues=expected_values,
                        ReturnValues=ANY,
                        ConditionExpression=ANY,
                    )
                    self.assertEqual(response, f"Immunization#{self.immunization['id']}")

    def test_update_immunization_not_found(self):
        """it should not update Immunization since the imms id not found"""

        with self.assertRaises(ResourceNotFoundError):
            self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.table.update_item.assert_not_called()

    def test_update_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.update_item = MagicMock(return_value=response)
        self.table.query = MagicMock(
            return_value={
                "Count": 1,
                "Items": [
                    {
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1,
                    }
                ],
            }
        )
        with self.assertRaises(UnhandledResponseError) as e:
            self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_update_immunization_unhandled_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        response = {"Error": {"Code": "InternalServerError"}}
        with unittest.mock.patch.object(
            self.table,
            "update_item",
            side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "UpdateItem"),
        ):
            with self.assertRaises(UnhandledResponseError) as e:
                self.table.query = MagicMock(
                    return_value={
                        "Count": 1,
                        "Items": [
                            {
                                "PK": _make_immunization_pk(imms_id),
                                "Resource": json.dumps(self.immunization),
                                "Version": 1,
                            }
                        ],
                    }
                )
                self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_update_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(
            self.table,
            "update_item",
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
            ),
        ):
            with self.assertRaises(ResourceNotFoundError):
                self.table.query = MagicMock(
                    return_value={
                        "Count": 1,
                        "Items": [
                            {
                                "PK": _make_immunization_pk(imms_id),
                                "Resource": json.dumps(self.immunization),
                                "Version": 1,
                            }
                        ],
                    }
                )
                self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)


class TestDeleteImmunization(TestImmunizationBatchRepository):
    def test_delete_immunization(self):
        """it should delete Immunization record"""

        test_item = {
            "PK": _make_immunization_pk(imms_id),
            "Resource": json.dumps(self.immunization),
            "Version": 1,
        }

        get_item_response = {
            "Item": test_item,
        }
        query_response = {
            "Count": 1,
            "Items": [test_item],
        }

        for last_imms_pk in [_make_immunization_pk(imms_id), None]:
            if last_imms_pk:
                self.table.get_item = MagicMock(return_value=get_item_response)
            else:
                self.table.query = MagicMock(return_value=query_response)
            response = self.repository.delete_immunization(
                self.immunization, "supplier", "vax-type", self.table, last_imms_pk
            )
            self.table.update_item.assert_called_with(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
                ExpressionAttributeValues={
                    ":timestamp": ANY,
                    ":operation": "DELETE",
                    ":supplier_system": "supplier",
                },
                ReturnValues=ANY,
                ConditionExpression=ANY,
            )
            self.assertEqual(response, f"Immunization#{self.immunization['id']}")

    def test_delete_immunization_not_found(self):
        """it should not delete Immunization since the imms id not found"""

        with self.assertRaises(ResourceNotFoundError):
            self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.table.update_item.assert_not_called()

    def test_delete_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.update_item = MagicMock(return_value=response)
        self.table.query = MagicMock(
            return_value={
                "Count": 1,
                "Items": [
                    {
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1,
                    }
                ],
            }
        )
        with self.assertRaises(UnhandledResponseError) as e:
            self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_delete_immunization_unhandled_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        response = {"Error": {"Code": "InternalServerError"}}
        with unittest.mock.patch.object(
            self.table,
            "update_item",
            side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "UpdateItem"),
        ):
            with self.assertRaises(UnhandledResponseError) as e:
                self.table.query = MagicMock(
                    return_value={
                        "Count": 1,
                        "Items": [
                            {
                                "PK": _make_immunization_pk(imms_id),
                                "Resource": json.dumps(self.immunization),
                                "Version": 1,
                            }
                        ],
                    }
                )
                self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_delete_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(
            self.table,
            "update_item",
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
            ),
        ):
            with self.assertRaises(ResourceNotFoundError):
                self.table.query = MagicMock(
                    return_value={
                        "Count": 1,
                        "Items": [
                            {
                                "PK": _make_immunization_pk(imms_id),
                                "Resource": json.dumps(self.immunization),
                                "Version": 1,
                            }
                        ],
                    }
                )
                self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)


@mock_aws
@patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "TestTable"})
class TestCreateTable(TestImmunizationBatchRepository):
    def test_create_table_success(self):
        """Test if create_table returns a DynamoDB Table instance with the correct name"""

        # Create a mock DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        table_name = os.environ["DYNAMODB_TABLE_NAME"]

        # Define table schema
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # Call the function
        table = create_table(region_name="eu-west-2")

        # Assertions
        self.assertEqual(table.table_name, table_name)
