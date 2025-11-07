import time
import unittest
import uuid
from unittest.mock import ANY, MagicMock, Mock, patch

import botocore.exceptions
import simplejson as json
from boto3.dynamodb.conditions import Attr, Key
from fhir.resources.R4B.immunization import Immunization

from common.models.api_errors import UnhandledResponseError
from common.models.errors import ResourceNotFoundError
from common.models.immunization_record_metadata import ImmunizationRecordMetadata
from common.models.utils.validation_utils import get_vaccine_type
from repository.fhir_repository import ImmunizationRepository
from testing_utils.generic_utils import update_target_disease_code
from testing_utils.immunization_utils import VALID_NHS_NUMBER, create_covid_immunization_dict


def _make_immunization_pk(_id):
    return f"Immunization#{_id}"


def _make_patient_pk(_id):
    return f"Patient#{_id}"


class TestFhirRepositoryBase(unittest.TestCase):
    """Base class for all tests to set up common fixtures"""

    def setUp(self):
        super().setUp()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("common.models.utils.validation_utils.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()


class TestGetImmunizationByIdentifier(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_immunization_by_identifier(self):
        """it should find an Immunization by id"""
        imms_id = "a-id#an-id"
        resource = dict()
        resource["Resource"] = {"foo": "bar", "id": "test"}
        self.table.query = MagicMock(
            return_value={
                "Items": [
                    {
                        "Resource": json.dumps({"foo": "bar", "id": "test"}),
                        "Version": 1,
                        "PatientSK": "COVID#2516525251",
                    }
                ]
            }
        )

        immunisation, immunisation_type = self.repository.get_immunization_by_identifier(imms_id)

        self.table.query.assert_called_once_with(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(imms_id),
        )

        self.assertDictEqual(immunisation["resource"], resource["Resource"])
        self.assertEqual(immunisation["version"], 1)
        self.assertEqual(immunisation["id"], "test")
        self.assertEqual(immunisation_type, "covid")

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.query = MagicMock(return_value={})

        immunisation, immunisation_type = self.repository.get_immunization_by_identifier(imms_id)
        self.assertIsNone(immunisation)
        self.assertIsNone(immunisation_type)

    def test_check_immunization_identifier_exists_returns_true(self):
        """it should return true when a record does exist with the given identifier"""
        imms_id = "https://system.com#id-123"
        self.table.query = MagicMock(
            return_value={
                "Items": [
                    {
                        "Resource": json.dumps({"item": "exists"}),
                        "Version": 1,
                        "PatientSK": "COVID#2516525251",
                        "IdentifierPK": "https://system.com#id-123",
                    }
                ]
            }
        )

        result = self.repository.check_immunization_identifier_exists("https://system.com", "id-123")

        self.table.query.assert_called_once_with(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(imms_id),
        )
        self.assertTrue(result)

    def test_check_immunization_identifier_exists_returns_false_when_no_record_exists(self):
        """it should return false when a record does not exist with the given identifier"""
        imms_id = "https://system.com#id-123"
        self.table.query = MagicMock(return_value={})

        result = self.repository.check_immunization_identifier_exists("https://system.com", "id-123")

        self.table.query.assert_called_once_with(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(imms_id),
        )
        self.assertFalse(result)


class TestGetImmunization(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_immunization_by_id(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        expected_resource = {"foo": "bar"}
        expected_version = 1
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps(expected_resource),
                    "Version": expected_version,
                    "PatientSK": "COVID#2516525251",
                }
            }
        )
        immunisation, resource_meta = self.repository.get_immunization_and_resource_meta_by_id(imms_id)

        # Validate the results
        self.assertDictEqual(expected_resource, immunisation)
        self.assertEqual(resource_meta.resource_version, expected_version)
        self.assertEqual(resource_meta.is_deleted, False)
        self.assertEqual(resource_meta.is_reinstated, False)
        self.table.get_item.assert_called_once_with(Key={"PK": _make_immunization_pk(imms_id)})

    def test_get_immunization_by_id_returns_reinstated_records(self):
        """it should find an Immunization by id, including reinstated records by default"""
        imms_id = "an-id"
        expected_resource = {"foo": "bar"}
        expected_version = 1
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps(expected_resource),
                    "Version": expected_version,
                    "DeletedAt": "reinstated",
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        immunisation, resource_meta = self.repository.get_immunization_and_resource_meta_by_id(imms_id)

        # Validate the results
        self.assertDictEqual(expected_resource, immunisation)
        self.assertEqual(resource_meta.resource_version, expected_version)
        self.assertEqual(resource_meta.is_deleted, False)
        self.assertEqual(resource_meta.is_reinstated, True)
        self.table.get_item.assert_called_once_with(Key={"PK": _make_immunization_pk(imms_id)})

    def test_get_immunization_by_id_returns_deleted_records_when_flag_is_set(self):
        """it should find an Immunization by id, including deleted records when the include_deleted flag is set True"""
        imms_id = "an-id"
        expected_resource = {"foo": "bar"}
        expected_version = 4
        self.table.get_item = MagicMock(
            return_value={
                "Item": {
                    "Resource": json.dumps(expected_resource),
                    "Version": expected_version,
                    "DeletedAt": time.time(),
                    "PatientSK": "COVID19#2516525251",
                }
            }
        )
        immunisation, resource_meta = self.repository.get_immunization_and_resource_meta_by_id(
            imms_id, include_deleted=True
        )

        # Validate the results
        self.assertDictEqual(expected_resource, immunisation)
        self.assertEqual(resource_meta.resource_version, expected_version)
        self.assertEqual(resource_meta.is_deleted, True)
        self.assertEqual(resource_meta.is_reinstated, False)
        self.table.get_item.assert_called_once_with(Key={"PK": _make_immunization_pk(imms_id)})

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.get_item = MagicMock(return_value={})

        imms, version = self.repository.get_immunization_and_resource_meta_by_id(imms_id)
        self.assertIsNone(imms)
        self.assertIsNone(version)

    def test_immunization_not_found_when_record_is_logically_deleted(self):
        """it should return None if Immunization is logically deleted and the include_deleted flag is set to False
        (default behaviour)"""
        imms_id = "a-deleted-id"
        self.table.get_item = MagicMock(return_value={"Item": {"Resource": "{}", "DeletedAt": time.time()}})

        imms, version = self.repository.get_immunization_and_resource_meta_by_id(imms_id, include_deleted=False)
        self.assertIsNone(imms)
        self.assertIsNone(version)


def _make_a_patient(nhs_number="1234567890") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "identifier": {"system": "a-system", "value": nhs_number},
    }


class TestCreateImmunizationMainIndex(TestFhirRepositoryBase):
    _MOCK_CREATED_UUID = "88ca94d9-4618-4dc1-9e94-e701d3b2dd06"

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id", "identifier": {"value": "an-identifier"}}

    def test_create_immunization(self):
        """it should create Immunization, and return created object unique ID"""
        imms = Immunization.parse_obj(create_covid_immunization_dict(imms_id=self._MOCK_CREATED_UUID))

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis

        created_id = self.repository.create_immunization(imms, "Test")

        self.assertEqual(created_id, self._MOCK_CREATED_UUID)
        self.table.put_item.assert_called_once_with(
            Item={
                "PK": f"Immunization#{self._MOCK_CREATED_UUID}",
                "PatientPK": "Patient#9990548609",
                "PatientSK": f"COVID#{self._MOCK_CREATED_UUID}",
                "Resource": imms.json(),
                "IdentifierPK": "https://supplierABC/identifiers/vacc#ACME-vacc123456",
                "Operation": "CREATE",
                "Version": 1,
                "SupplierSystem": "Test",
            }
        )

    def test_create_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.put_item = MagicMock(return_value=response)
        self.table.query = MagicMock(return_value={})

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.create_immunization(Immunization.parse_obj(create_covid_immunization_dict("an-id")), "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)


class TestCreateImmunizationPatientIndex(TestFhirRepositoryBase):
    """create_immunization should create a patient record with vaccine type"""

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id"}

    def test_create_patient_gsi(self):
        """create Immunization method should create Patient index with nhs-number as ID and no system"""
        imms = create_covid_immunization_dict("an-id")

        nhs_number = "1234567890"
        imms["contained"][1]["identifier"][0]["value"] = nhs_number

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        # When
        _ = self.repository.create_immunization(Immunization.parse_obj(imms), "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["PatientPK"], f"Patient#{nhs_number}")

    def test_create_patient_with_vaccine_type(self):
        """Patient record should have a sort-key based on vaccine-type"""
        imms = create_covid_immunization_dict("an-id")

        update_target_disease_code(imms, "FLU")
        vaccine_type = get_vaccine_type(imms)

        self.table.query = MagicMock(return_value={"Count": 0})
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})

        # When
        _ = self.repository.create_immunization(Immunization.parse_obj(imms), "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(item["PatientSK"].startswith(f"{vaccine_type}#"))


class TestUpdateImmunization(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)

    def test_update_immunisation_is_successful(self):
        """it should update the immunisation record"""
        imms_id = "an-imms-id"
        imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        existing_record_metadata = ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False)

        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        self.table.update_item = MagicMock(return_value=dynamo_response)

        # When
        updated_version = self.repository.update_immunization(imms_id, imms, existing_record_metadata, "Test")

        # Then
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
                ":timestamp": ANY,
                ":patient_pk": _make_patient_pk(patient_id),
                ":patient_sk": patient_sk,
                ":imms_resource_val": json.dumps(imms),
                ":operation": "UPDATE",
                ":version": 2,
                ":supplier_system": "Test",
            },
            ConditionExpression=ANY,
        )
        self.assertEqual(updated_version, 2)

    def test_update_immunisation_is_successful_when_record_needs_to_be_reinstated(self):
        """it should reinstate a deleted record when requested via the update operation"""
        imms_id = "an-imms-id"
        imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        existing_record_metadata = ImmunizationRecordMetadata(resource_version=2, is_deleted=True, is_reinstated=False)

        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        self.table.update_item = MagicMock(return_value=dynamo_response)

        # When
        updated_version = self.repository.update_immunization(imms_id, imms, existing_record_metadata, "Test")

        # Then
        update_exp = (
            "SET UpdatedAt = :timestamp, PatientPK = :patient_pk, PatientSK = :patient_sk, "
            "#imms_resource = :imms_resource_val, Operation = :operation, Version = :version, DeletedAt = :respawn, "
            "SupplierSystem = :supplier_system "
        )
        patient_id = imms["contained"][1]["identifier"][0]["value"]
        vaccine_type = get_vaccine_type(imms)
        patient_sk = f"{vaccine_type}#{imms_id}"

        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression=update_exp,
            ExpressionAttributeNames={"#imms_resource": "Resource"},
            ExpressionAttributeValues={
                ":timestamp": ANY,
                ":patient_pk": _make_patient_pk(patient_id),
                ":patient_sk": patient_sk,
                ":imms_resource_val": json.dumps(imms),
                ":operation": "UPDATE",
                ":version": 3,
                ":supplier_system": "Test",
                ":respawn": "reinstated",
            },
            ConditionExpression=ANY,
        )
        self.assertEqual(updated_version, 3)

    def test_update_throws_error_when_response_can_not_be_handled(self):
        """it should throw a ResourceNotFoundError when the conditional check fails. (This is a fairly unlikely race
        condition, as a check is made first to retrieve the record."""
        imms_id = "an-id"
        imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        existing_record_metadata = ImmunizationRecordMetadata(resource_version=2, is_deleted=True, is_reinstated=False)

        error_res = {"Error": {"Code": "ConditionalCheckFailedException"}}
        self.table.update_item.side_effect = botocore.exceptions.ClientError(
            error_response=error_res, operation_name="Update"
        )

        with self.assertRaises(ResourceNotFoundError) as e:
            # When
            self.repository.update_immunization(imms_id, imms, existing_record_metadata, "Test")

        # Then
        self.assertEqual(str(e.exception), "Immunization resource does not exist. ID: an-id")


class TestDeleteImmunization(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_delete_immunization(self):
        """it should logically delete Immunization by setting DeletedAt attribute"""
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
            self.repository.delete_immunization(imms_id, "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
            ExpressionAttributeValues={
                ":timestamp": now_epoch,
                ":operation": "DELETE",
                ":supplier_system": "Test",
            },
            ConditionExpression=ANY,
        )

    def test_multiple_delete_should_not_update_timestamp(self):
        """when delete is called multiple times, or when it doesn't exist, it should not update DeletedAt,
        and it should return Error"""
        imms_id = "an-id"
        error_res = {"Error": {"Code": "ConditionalCheckFailedException"}}
        self.table.update_item.side_effect = botocore.exceptions.ClientError(
            error_response=error_res, operation_name="an-op"
        )

        with self.assertRaises(ResourceNotFoundError) as e:
            self.repository.delete_immunization(imms_id, "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key=ANY,
            UpdateExpression=ANY,
            ExpressionAttributeValues=ANY,
            ConditionExpression=Attr("PK").eq(_make_immunization_pk(imms_id))
            & (Attr("DeletedAt").not_exists() | Attr("DeletedAt").eq("reinstated")),
        )

        self.assertIsInstance(e.exception, ResourceNotFoundError)
        self.assertEqual(e.exception.resource_id, imms_id)
        self.assertEqual(e.exception.resource_type, "Immunization")

    def test_delete_throws_error_when_response_can_not_be_handled(self):
        """it should re-raise the exception to be handled at the controller layer when an unexpected exception occurs
        interacting with DynamoDB"""
        imms_id = "an-id"
        error_res = {"Error": {"Code": "UnexpectedError e.g. service down"}}
        self.table.update_item.side_effect = botocore.exceptions.ClientError(
            error_response=error_res, operation_name="an-op"
        )

        with self.assertRaises(botocore.exceptions.ClientError) as e:
            # When
            self.repository.delete_immunization(imms_id, "Test")

        # Then
        self.assertEqual(e.exception.response, error_res)


class TestFindImmunizations(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_warning_patcher = patch("logging.Logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_find_immunizations(self):
        """it should find events with patient_identifier"""
        nhs_number = "a-patient-id"
        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": []}
        self.table.query = MagicMock(return_value=dynamo_response)

        condition = Key("PatientPK").eq(_make_patient_pk(nhs_number))

        # When
        _ = self.repository.find_immunizations(nhs_number, vaccine_types={"COVID"})

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
        _ = self.repository.find_immunizations("an-id", {"COVID"})

        # Then
        self.table.query.assert_called_once_with(
            IndexName="PatientGSI", KeyConditionExpression=ANY, FilterExpression=is_
        )

    def test_map_results_to_immunizations(self):
        """it should map Resource list into a list of Immunizations"""
        imms1 = {"id": 1, "meta": {"versionId": 1}}
        imms2 = {"id": 2, "meta": {"versionId": 1}}
        items = [
            {
                "Resource": json.dumps(imms1),
                "PatientSK": "COVID#some_other_text",
                "Version": "1",
            },
            {
                "Resource": json.dumps(imms2),
                "PatientSK": "COVID#some_other_text",
                "Version": "1",
            },
        ]

        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": items}
        self.table.query = MagicMock(return_value=dynamo_response)

        # When
        results = self.repository.find_immunizations("an-id", {"COVID"})

        # Then
        self.assertListEqual(results, [imms1, imms2])

    def test_bad_response_from_dynamo(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.query = MagicMock(return_value=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.find_immunizations("an-id", {"COVID"})

        # Then
        self.assertDictEqual(e.exception.response, response)


class TestImmunizationDecimals(TestFhirRepositoryBase):
    """It should create a record and keep decimal precision"""

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id", "identifier": {"value": "an-identifier"}}

    def test_decimal_on_create(self):
        """it should create Immunization, and preserve decimal value"""
        imms = create_covid_immunization_dict(imms_id="an-id")
        imms["doseQuantity"]["value"] = 0.7477

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(Immunization.parse_obj(imms), "Test")

        self.assertEqual(res_imms, "an-id")

        self.table.put_item.assert_called_once()

        expected_item = {
            "PK": ANY,
            "PatientPK": ANY,
            "PatientSK": ANY,
            "Resource": Immunization.parse_obj(imms).json(use_decimal=True),
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
            resource_from_item["doseQuantity"]["value"],
            0.7477,
        )

        self.table.put_item.assert_called_once()

    def run_update_immunization_test(self, imms_id, imms, updated_dose_quantity=None):
        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        self.table.update_item = MagicMock(return_value=dynamo_response)
        existing_record_metadata = ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False)

        # When
        updated_version = self.repository.update_immunization(imms_id, imms, existing_record_metadata, "Test")
        self.assertEqual(updated_version, 2)

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
                ":timestamp": ANY,
                ":patient_pk": _make_patient_pk(patient_id),
                ":patient_sk": patient_sk,
                ":imms_resource_val": json.dumps(imms, use_decimal=True),
                ":operation": "UPDATE",
                ":version": 2,
                ":supplier_system": "Test",
            },
            ConditionExpression=ANY,
        )

        if updated_dose_quantity is not None:
            imms_resource_val = json.loads(
                self.table.update_item.call_args.kwargs["ExpressionAttributeValues"][":imms_resource_val"]
            )
            self.assertEqual(imms_resource_val["doseQuantity"]["value"], updated_dose_quantity)

    def test_decimal_on_update(self):
        """it should update record when replacing doseQuantity and keep decimal precision"""
        imms_id = "an-imms-id"
        imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        updated_dose_quantity = 0.7566
        imms["doseQuantity"]["value"] = updated_dose_quantity
        self.run_update_immunization_test(imms_id, imms, updated_dose_quantity)

    def test_decimal_on_update_patient(self):
        """it should update record by replacing both Immunization and Patient and dose quantity"""
        imms_id = "an-imms-id"
        imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        updated_dose_quantity = 0.7566
        imms["doseQuantity"]["value"] = updated_dose_quantity
        imms["patient"] = self.patient
        self.run_update_immunization_test(imms_id, imms, updated_dose_quantity)
