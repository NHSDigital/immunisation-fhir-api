import os
import unittest
from unittest.mock import MagicMock, ANY, patch
import boto3
import simplejson as json
import botocore.exceptions
from moto import mock_aws
from uuid import uuid4
from models.errors import IdentifierDuplicationError, ResourceNotFoundError, UnhandledResponseError, ResourceFoundError
from fhir_batch_repository import ImmunizationBatchRepository, create_table
from tests.utils.immunization_utils import create_covid_19_immunization_dict

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
        self.immunization = create_covid_19_immunization_dict(imms_id)
        self.table.update_item = MagicMock(return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()

    def tearDown(self):
        self.redis_patcher.stop()
        return super().tearDown()

class TestCreateImmunization(TestImmunizationBatchRepository): 
    
    def modify_immunization(self, remove_nhs):
        """Modify the immunization object by removing NHS number if required"""
        if remove_nhs:
            for i, x in enumerate(self.immunization["contained"]):
                if x["resourceType"] == "Patient":
                    del self.immunization["contained"][i]
                    break

    def create_immunization_test_logic(self, is_present, remove_nhs):
        """Common logic for testing immunization creation."""
        self.mock_redis_client.hget.side_effect = ['COVID19']
        self.modify_immunization(remove_nhs)

        self.repository.create_immunization(
            self.immunization, "supplier", "vax-type", self.table, is_present
        )
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
            ConditionExpression=ANY
        )
        self.assertEqual(item["PK"], f'Immunization#{self.immunization["id"]}')

    def test_create_immunization_with_nhs_number(self):
        """Test creating Immunization with NHS number."""
        self.create_immunization_test_logic(is_present=True, remove_nhs=False)

    def test_create_immunization_without_nhs_number(self):
        """Test creating Immunization without NHS number."""
        
        self.create_immunization_test_logic(is_present=False, remove_nhs=True)    


    def test_create_immunization_duplicate(self):
        """it should not create Immunization since the request is duplicate"""
        self.table.query = MagicMock(return_value={
            "id": imms_id,
            "identifier": [{"system": "test-system", "value": "12345"}],
            "contained": [{"resourceType": "Patient", "identifier": [{"value": "98765"}]}],
            "Count": 1
        })
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

        response = {'Error': {'Code': 'InternalServerError'}}
        with unittest.mock.patch.object(self.table, 'put_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")):
            with self.assertRaises(UnhandledResponseError) as e:
                self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)

    def test_create_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(self.table, 'put_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")):
            with self.assertRaises(ResourceFoundError):
                self.repository.create_immunization(self.immunization, "supplier", "vax-type", self.table, False)              
        

class TestUpdateImmunization(TestImmunizationBatchRepository): 
    def test_update_immunization(self):
        """it should update Immunization record"""

        test_cases = [
            # Update scenario
            {
                "query_response": {
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                },
                "expected_extra_values": {}  # No extra assertion values
            },
            # Reinstated scenario
            {
                "query_response": {
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1,
                        "DeletedAt": "20210101"
                    }]
                },
                "expected_extra_values": {":respawn": "reinstated"}
            },
            # Update reinstated scenario
            {
                "query_response": {
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1,
                        "DeletedAt": "reinstated"
                    }]
                },
                "expected_extra_values": {}
            }
        ] 
        for is_present in [True, False]:
            for case in test_cases:
                with self.subTest(is_present=is_present, case=case):
                    self.table.query = MagicMock(return_value=case["query_response"])
                    response = self.repository.update_immunization(
                        self.immunization, "supplier", "vax-type", self.table, is_present
                    )
                    expected_values = {
                        ":timestamp": ANY,
                        ":patient_pk": ANY,
                        ":patient_sk": ANY,
                        ":imms_resource_val": json.dumps(self.immunization),
                        ":operation": "UPDATE",
                        ":version": 2,
                        ":supplier_system": "supplier"
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
                    self.assertEqual(response, f'Immunization#{self.immunization["id"]}')
    
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
        self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
        with self.assertRaises(UnhandledResponseError) as e:
            self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)  

    def test_update_immunization_unhandled_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        response = {'Error': {'Code': 'InternalServerError'}}
        with unittest.mock.patch.object(self.table, 'update_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "UpdateItem")):
            with self.assertRaises(UnhandledResponseError) as e:
                self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
                self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)    
        self.assertDictEqual(e.exception.response, response)

    def test_update_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(self.table, 'update_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")):
            with self.assertRaises(ResourceNotFoundError) as e:
                self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
                self.repository.update_immunization(self.immunization, "supplier", "vax-type", self.table, False)    
          
class TestDeleteImmunization(TestImmunizationBatchRepository): 
    def test_delete_immunization(self):
        """it should delete Immunization record"""

        self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
        for is_present in [True, False]:
            response = self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, is_present)
            self.table.update_item.assert_called_with(
                Key={"PK": _make_immunization_pk(imms_id)},
                UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
                ExpressionAttributeValues={":timestamp": ANY, ":operation": "DELETE", ":supplier_system": "supplier"},
                ReturnValues=ANY,
                ConditionExpression=ANY,
            )
            self.assertEqual(response, f'Immunization#{self.immunization ["id"]}')  

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
        self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
        with self.assertRaises(UnhandledResponseError) as e:
            self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)
        self.assertDictEqual(e.exception.response, response)  

    def test_delete_immunization_unhandled_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        response = {'Error': {'Code': 'InternalServerError'}}
        with unittest.mock.patch.object(self.table, 'update_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "InternalServerError"}}, "UpdateItem")):
            with self.assertRaises(UnhandledResponseError) as e:
                self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
                }
            )
                self.repository.delete_immunization(self.immunization, "supplier", "vax-type", self.table, False)    
        self.assertDictEqual(e.exception.response, response)

    def test_delete_immunization_conditionalcheckfailedexception_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        with unittest.mock.patch.object(self.table, 'update_item', side_effect=botocore.exceptions.ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")):
            with self.assertRaises(ResourceNotFoundError) as e:
                self.table.query = MagicMock(return_value={
                    "Count": 1,
                    "Items": [{
                        "PK": _make_immunization_pk(imms_id),
                        "Resource": json.dumps(self.immunization),
                        "Version": 1
                    }]
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
