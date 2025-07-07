import simplejson as json
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch, ANY

import botocore.exceptions
from boto3.dynamodb.conditions import Attr, Key
from fhir_repository import ImmunizationRepository
from models.utils.validation_utils import get_vaccine_type
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    IdentifierDuplicationError,
    UnauthorizedVaxError,
    UnauthorizedVaxOnRecordError
)
from tests.utils.generic_utils import update_target_disease_code
from tests.utils.immunization_utils import create_covid_19_immunization_dict

def _make_immunization_pk(_id):
    return f"Immunization#{_id}"


def _make_patient_pk(_id):
    return f"Patient#{_id}"

class TestFhirRepositoryBase(unittest.TestCase):
    """Base class for all tests to set up common fixtures"""

    def setUp(self):
        super().setUp()
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.redis_patcher.stop()
        self.logger_info_patcher.stop()
        super().tearDown()


class TestGetImmunizationByIdentifier(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)

    def tearDown(self):
        self.redis_patcher.stop()
        super().tearDown()

    def test_get_immunization_by_identifier(self):
        """it should find an Immunization by id"""
        imms_id = "a-id#an-id"
        resource = dict()
        resource["Resource"] = {"id": "test", "version": 1}
        self.table.query = MagicMock(
            return_value={
                "Items": [
                    {
                        "Resource": json.dumps({"foo": "bar", "id": "test"}),
                        "Version": 1,
                        "PatientSK": "COVID19#2516525251",
                    }
                ]
            }
        )

        imms = self.repository.get_immunization_by_identifier(imms_id, ["COVID19.CRUDS"])

        # Validate the results
        self.assertDictEqual(resource["Resource"], imms)
        # self.table.get_item.assert_called_once_with(Key={"PK": (imms_id)})
        self.table.query.assert_called_once_with(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(imms_id),
        )

    def test_unauthorized_get_immunization_by_identifier(self):
        """it should not get an Immunization by id if vax perms do not exist"""
        imms_id = "a-id#an-id"
        resource = dict()
        resource["Resource"] = {"foo": "bar"}
        resource["Version"] = 1
        self.table.query = MagicMock(
            return_value={
                "Items": [
                    {
                        "Resource": json.dumps({"foo": "bar", "id": "test"}),
                        "Version": 1,
                        "PatientSK": "COVID19#2516525251",
                    }
                ]
            }
        )
        with self.assertRaises(UnauthorizedVaxError) as e:
            # When
            self.repository.get_immunization_by_identifier(imms_id, ["FLU.CRUD"])

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.query = MagicMock(return_value={})

        imms = self.repository.get_immunization_by_identifier(imms_id, ["COVID19.CRUD"])
        self.assertIsNone(imms)


class TestGetImmunization(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)

    def test_get_immunization_by_id(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        resource = dict()
        resource["Resource"] = {"foo": "bar"}
        resource["Version"] = 1
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        imms = self.repository.get_immunization_by_id(imms_id, ["COVID19.CRUDS"])

        # Validate the results
        self.assertDictEqual(resource, imms)
        self.table.get_item.assert_called_once_with(Key={"PK": _make_immunization_pk(imms_id)})

    def test_unauthorized_get_immunization_by_id(self):
        """it should not get an Immunization by id if vax perms do not exist"""
        imms_id = "an-id"
        resource = dict()
        resource["Resource"] = {"foo": "bar"}
        resource["Version"] = 1
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        with self.assertRaises(UnauthorizedVaxError) as e:
            # When
            self.repository.get_immunization_by_id(imms_id, ["FLU.CRUD"])

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.get_item = MagicMock(return_value={})

        imms = self.repository.get_immunization_by_id(imms_id, ["COVID19.CRUD"])
        self.assertIsNone(imms)


def _make_a_patient(nhs_number="1234567890") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "identifier": {"system": "a-system", "value": nhs_number},
    }


class TestCreateImmunizationMainIndex(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id", "identifier": {"value": "an-identifier"}}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_create_immunization(self):
        """it should create Immunization, and return created object"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict(imms_id="an-id")

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        self.assertDictEqual(res_imms, imms)
        self.table.put_item.assert_called_once_with(
            Item={
                "PK": ANY,
                "PatientPK": ANY,
                "PatientSK": ANY,
                "Resource": json.dumps(imms),
                "IdentifierPK": ANY,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": "Test",
            }
        )

    def test_create_immunization_batch(self):
        """it should create Immunization, and return created object"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict(imms_id="an-id")

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, None, ["COVID19.CRUD"], "Test")

        self.assertDictEqual(res_imms, imms)
        self.table.put_item.assert_called_once_with(
            Item={
                "PK": ANY,
                "PatientPK": ANY,
                "PatientSK": ANY,
                "Resource": json.dumps(imms),
                "IdentifierPK": ANY,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": "Test",
            }
        )

    def test_add_patient(self):
        """it should store patient along the Immunization resource"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict("an-id")
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        self.assertDictEqual(res_imms, imms)
        self.table.put_item.assert_called_once_with(
            Item={
                "PK": ANY,
                "PatientPK": ANY,
                "PatientSK": ANY,
                "Resource": ANY,
                "IdentifierPK": ANY,
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": "Test",
            }
        )

    def test_create_immunization_makes_new_id(self):
        """create should create new Logical ID even if one is already provided"""
        imms_id = "original-id-from-request"

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict(imms_id)
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        _ = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(item["PK"].startswith("Immunization#"))
        self.assertNotEqual(item["PK"], "Immunization#original-id-from-request")

    def test_create_immunization_returns_new_id(self):
        """create should return the persisted object i.e. with new id"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "original-id-from-request"
        imms = create_covid_19_immunization_dict(imms_id)
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        response = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        self.assertNotEqual(response["id"], imms_id)

    def test_create_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        self.mock_redis_client.hget.return_value = "COVID19"
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.put_item = MagicMock(return_value=response)
        self.table.query = MagicMock(return_value={})

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.create_immunization(
                create_covid_19_immunization_dict("an-id"), self.patient, ["COVID19.CRUD"], "Test"
            )

        # Then
        self.assertDictEqual(e.exception.response, response)

    def test_create_throws_error_when_identifier_already_in_dynamodb(self):
        """it should throw UnhandledResponse when trying to update an immunization with an identfier that is already stored"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient

        self.table.query = MagicMock(return_value={"Items": [{"Resource": '{"id": "different-id"}'}], "Count": 1})
        identifier = f"{imms['identifier'][0]['system']}#{imms['identifier'][0]['value']}"
        with self.assertRaises(IdentifierDuplicationError) as e:
            # When
            self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        self.assertEqual(str(e.exception), f"The provided identifier: {identifier} is duplicated")


class TestCreateImmunizationPatientIndex(TestFhirRepositoryBase):
    """create_immunization should create a patient record with vaccine type"""

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id"}

    def tearDown(self):
        super().tearDown()

    def test_create_patient_gsi(self):
        """create Immunization method should create Patient index with nhs-number as ID and no system"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict("an-id")

        nhs_number = "1234567890"
        imms["contained"][1]["identifier"][0]["value"] = nhs_number

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        # When
        _ = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["PatientPK"], f"Patient#{nhs_number}")

    def test_create_patient_with_vaccine_type(self):
        """Patient record should have a sort-key based on vaccine-type"""
        self.mock_redis_client.hget.return_value = "FLU"
        imms = create_covid_19_immunization_dict("an-id")

        update_target_disease_code(imms, "FLU")
        vaccine_type = get_vaccine_type(imms)

        self.table.query = MagicMock(return_value={"Count": 0})
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})

        # When
        _ = self.repository.create_immunization(imms, self.patient, ["FLU.CRUD"], "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(item["PatientSK"].startswith(f"{vaccine_type}#"))

    def test_create_patient_with_unauthorised_vaccine_type_permissions(self):
        """Patient record should not be created"""
        imms = create_covid_19_immunization_dict("an-id")

        self.repository.table.query.return_value = {
            "Count": 0,
            "Items": []
        }

        self.repository.table.put_item.return_value = {
            "ResponseMetadata": {
                "HTTPStatusCode": 200
            }
        }

        update_target_disease_code(imms, "FLU")
        with self.assertRaises(UnauthorizedVaxError) as e:
            # When
            self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")
            


class TestUpdateImmunization(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = _make_a_patient("update-patient-id")

    def tearDown(self):
        return super().tearDown()

    def test_update1(self):
        """it should update record by replacing both Immunization and Patient"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-imms-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient

        resource = {"foo": "bar"}  # making sure we return updated imms from dynamodb
        dynamo_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": json.dumps(resource)},
        }
        self.table.update_item = MagicMock(return_value=dynamo_response)
        self.table.query = MagicMock(return_value={})

        now_epoch = 123456
        with patch("time.time") as mock_time:
            mock_time.return_value = now_epoch
            # When

            act_resource = self.repository.update_immunization(
                imms_id, imms, self.patient, 1, ["COVID19.CRUD"], "Test"
            )

        # Then
        self.assertDictEqual(act_resource, resource)

        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, "
            "Operation = :operation, Version = :version, SupplierSystem = :supplier_system "
        )
        patient_id = imms["contained"][1]["identifier"][0]["value"]
        vaccine_type = get_vaccine_type(imms)

        patient_sk = f"{vaccine_type}#{imms_id}"

        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression=update_exp,
            ExpressionAttributeNames={"#imms_resource": "Resource"},
            ExpressionAttributeValues={
                ":timestamp": now_epoch,
                ":patient_pk": _make_patient_pk(patient_id),
                ":patient_sk": patient_sk,
                ":imms_resource_val": json.dumps(imms),
                ":operation": "UPDATE",
                ":version": 2,
                ":supplier_system": "Test",
            },
            ReturnValues=ANY,
            ConditionExpression=ANY,
        )

    def test_update_throws_error_when_response_can_not_be_handled(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient

        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.update_item = MagicMock(return_value=response)
        self.table.query = MagicMock(return_value={})

        with self.assertRaises(UnhandledResponseError) as e:
            # When

            self.repository.update_immunization(imms_id, imms, self.patient, 1, ["COVID19.CRUD"], "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)

    def test_update_throws_error_when_identifier_already_in_dynamodb(self):
        """it should throw IdentifierDuplicationError when trying to update an immunization with an identfier that is already stored"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient
        identifier = f"{imms['identifier'][0]['system']}#{imms['identifier'][0]['value']}"
        self.table.query = MagicMock(return_value={"Items": [{"Resource": '{"id": "different-id"}'}], "Count": 1})

        with self.assertRaises(IdentifierDuplicationError) as e:
            # When

            self.repository.update_immunization(imms_id, imms, self.patient, 1, ["COVID19.CRUD"], "Test")

        self.assertEqual(str(e.exception), f"The provided identifier: {identifier} is duplicated")


class TestDeleteImmunization(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)

    def test_get_deleted_immunization(self):
        """it should return None if Immunization is logically deleted"""
        imms_id = "a-deleted-id"
        self.table.get_item = MagicMock(return_value={"Item": {"Resource": "{}", "DeletedAt": time.time()}})

        imms = self.repository.get_immunization_by_id(imms_id, ["COVID19.CRUD"])
        self.assertIsNone(imms)

    def test_delete_immunization(self):
        """it should logical delete Immunization by setting DeletedAt attribute"""
        imms_id = "an-id"
        dynamo_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": "{}"},
        }
        self.table.update_item = MagicMock(return_value=dynamo_response)

        now_epoch = 123456
        with patch("time.time") as mock_time:
            mock_time.return_value = now_epoch
            # When
            _id = self.repository.delete_immunization(imms_id, "COVID:delete", "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
            ExpressionAttributeValues={":timestamp": now_epoch, ":operation": "DELETE", ":supplier_system": "Test"},
            ReturnValues=ANY,
            ConditionExpression=ANY,
        )

    def test_delete_returns_old_resource(self):
        """it should return existing Immunization when delete is successful"""

        imms_id = "an-id"
        resource = {"foo": "bar"}
        dynamo_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": json.dumps(resource)},
        }
        self.table.update_item = MagicMock(return_value=dynamo_response)
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )

        now_epoch = 123456
        with patch("time.time") as mock_time:
            mock_time.return_value = now_epoch
            # When

            act_resource = self.repository.delete_immunization(imms_id, ["COVID19.CRUD"], "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key=ANY,
            UpdateExpression=ANY,
            ExpressionAttributeValues=ANY,
            ConditionExpression=ANY,
            ReturnValues="ALL_NEW",
        )
        self.assertDictEqual(act_resource, resource)

    def test_unauthorised_vax_delete(self):
        """when delete is called for a resource without proper vax permission"""
        imms_id = "an-id"
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "FLU#2516525251",
                    "DeletedAt": "reinstated"
                }
            }
        )

        self.repository.table.update_item.return_value = {
        "ResponseMetadata": {
            "HTTPStatusCode": 200
        },
        "Attributes": {
            "Resource": json.dumps({"id": "valid-id", "status": "deleted"})
        }
    }

        with self.assertRaises(UnauthorizedVaxError) as e:
            self.repository.delete_immunization(imms_id, ["COVID19.CRUD"], "Test")

    def test_multiple_delete_should_not_update_timestamp(self):
        """when delete is called multiple times, or when it doesn't exist, it should not update DeletedAt,
        and it should return Error"""
        imms_id = "an-id"
        error_res = {"Error": {"Code": "ConditionalCheckFailedException"}}
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        self.table.update_item.side_effect = botocore.exceptions.ClientError(
            error_response=error_res, operation_name="an-op"
        )

        with self.assertRaises(ResourceNotFoundError) as e:
            self.repository.delete_immunization(imms_id, ["COVID19.CRUD"], "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key=ANY,
            UpdateExpression=ANY,
            ExpressionAttributeValues=ANY,
            ReturnValues=ANY,
            ConditionExpression=Attr("PK").eq(_make_immunization_pk(imms_id))
            & (Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")),
        )

        self.assertIsInstance(e.exception, ResourceNotFoundError)
        self.assertEqual(e.exception.resource_id, imms_id)
        self.assertEqual(e.exception.resource_type, "Immunization")

    def test_delete_throws_error_when_response_can_not_be_handled(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        imms_id = "an-id"
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps({"foo": "bar"}),
                    "Version": 1,
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        self.table.update_item = MagicMock(return_value=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.delete_immunization(imms_id, ["COVID19.CRUD"], "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)


class TestFindImmunizations(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)

    def test_find_immunizations(self):
        """it should find events with patient_identifier"""
        nhs_number = "a-patient-id"
        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": []}
        self.table.query = MagicMock(return_value=dynamo_response)

        condition = Key("PatientPK").eq(_make_patient_pk(nhs_number))

        # When
        _ = self.repository.find_immunizations(nhs_number, vaccine_types=["COVID19"])

        # Then
        self.table.query.assert_called_once_with(
            IndexName="PatientGSI",
            KeyConditionExpression=condition,
            FilterExpression=ANY,
        )

    def test_exclude_deleted(self):
        """it should exclude records with DeletedAt attribute"""
        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": []}
        self.table.query = MagicMock(return_value=dynamo_response)

        is_ = Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")

        # When
        _ = self.repository.find_immunizations("an-id", ["COVID19"])

        # Then
        self.table.query.assert_called_once_with(
            IndexName="PatientGSI", KeyConditionExpression=ANY, FilterExpression=is_
        )

    def test_map_results_to_immunizations(self):
        """it should map Resource list into a list of Immunizations"""
        imms1 = {"id": 1}
        imms2 = {"id": 2}
        items = [
            {
                "Resource": json.dumps(imms1),
                "PatientSK": "COVID19#some_other_text",
            },
            {
                "Resource": json.dumps(imms2),
                "PatientSK": "COVID19#some_other_text",
            },
        ]

        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": items}
        self.table.query = MagicMock(return_value=dynamo_response)

        # When
        results = self.repository.find_immunizations("an-id", ["COVID19"])

        # Then
        self.assertListEqual(results, [imms1, imms2])

    def test_bad_response_from_dynamo(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.query = MagicMock(return_value=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.find_immunizations("an-id", ["COVID19"])

        # Then
        self.assertDictEqual(e.exception.response, response)


class TestImmunizationDecimals(TestFhirRepositoryBase):
    """It should create a record and keep decimal precision"""

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id", "identifier": {"value": "an-identifier"}}

    def tearDown(self):
        return super().tearDown()

    def test_decimal_on_create(self):
        """it should create Immunization, and preserve decimal value"""

        self.mock_redis_client.hget.return_value = "COVID19"
        imms = create_covid_19_immunization_dict(imms_id="an-id")
        imms["doseQuantity"] = 0.7477

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, ["COVID19.CRUD"], "Test")

        self.assertEqual(res_imms["doseQuantity"], imms["doseQuantity"])
        self.assertDictEqual(res_imms, imms)

        self.table.put_item.assert_called_once()

        expected_item = {
            "PK": ANY,
            "PatientPK": ANY,
            "PatientSK": ANY,
            "Resource": json.dumps(imms, use_decimal=True),
            "IdentifierPK": ANY,
            "Operation": "CREATE",
            "Version": 1,
            "SupplierSystem": "Test",
        }

        # Assert that put_item was called with the expected data
        item_passed_to_put_item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(all(item in expected_item.items() for item in item_passed_to_put_item.items()))

        resource_from_item = json.loads(item_passed_to_put_item["Resource"])
        self.assertEqual(
            resource_from_item["doseQuantity"],
            0.7477,
        )

        self.table.put_item.assert_called_once()

    def run_update_immunization_test(self, imms_id, imms, resource, updated_dose_quantity=None):
        dynamo_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": json.dumps(resource)},
        }
        self.table.update_item = MagicMock(return_value=dynamo_response)
        self.table.query = MagicMock(return_value={})
        now_epoch = 123456
        with patch("time.time") as mock_time:
            mock_time.return_value = now_epoch
            act_resource = self.repository.update_immunization(
                imms_id, imms, self.patient, 1, ["COVID19.CRUD"], "Test"
            )
        self.assertDictEqual(act_resource, resource)

        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, "
            "PatientSK = :patient_sk, #imms_resource = :imms_resource_val, "
            "Operation = :operation, Version = :version, SupplierSystem = :supplier_system "
        )
        patient_id = self.patient["identifier"]["value"]
        patient_id = imms["contained"][1]["identifier"][0]["value"]
        vaccine_type = get_vaccine_type(imms)
        patient_sk = f"{vaccine_type}#{imms_id}"

        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression=update_exp,
            ExpressionAttributeNames={"#imms_resource": "Resource"},
            ExpressionAttributeValues={
                ":timestamp": now_epoch,
                ":patient_pk": _make_patient_pk(patient_id),
                ":patient_sk": patient_sk,
                ":imms_resource_val": json.dumps(imms, use_decimal=True),
                ":operation": "UPDATE",
                ":version": 2,
                ":supplier_system": "Test",
            },
            ReturnValues=ANY,
            ConditionExpression=ANY,
        )

        if updated_dose_quantity is not None:
            imms_resource_val = json.loads(
                self.table.update_item.call_args.kwargs["ExpressionAttributeValues"][":imms_resource_val"]
            )
            self.assertEqual(imms_resource_val["doseQuantity"], updated_dose_quantity)

    def test_decimal_on_update(self):
        """it should update record when replacing doseQuantity and keep decimal precision"""
        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-imms-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["doseQuantity"] = 1.5556
        updated_dose_quantity = 0.7566
        imms["doseQuantity"] = updated_dose_quantity
        imms["patient"] = self.patient
        resource = imms
        self.run_update_immunization_test(imms_id, imms, resource, updated_dose_quantity)

    def test_decimal_on_update_patient(self):
        """it should update record by replacing both Immunization and Patient and dosequantity"""
        self.mock_redis_client.hget.return_value = "COVID19"
        imms_id = "an-imms-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["doseQuantity"] = 1.590
        imms["patient"] = self.patient
        resource = {"doseQuantity": 1.590, "foo": "bar"}
        self.run_update_immunization_test(imms_id, imms, resource)
