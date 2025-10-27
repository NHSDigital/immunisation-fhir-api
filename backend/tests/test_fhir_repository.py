import time
import unittest
import uuid
from unittest.mock import ANY, MagicMock, patch

import botocore.exceptions
import simplejson as json
from boto3.dynamodb.conditions import Attr, Key
from fhir_repository import ImmunizationRepository
from models.errors import IdentifierDuplicationError, ResourceNotFoundError, UnhandledResponseError
from models.utils.validation_utils import get_vaccine_type
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
                        "PatientSK": "COVID19#2516525251",
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
        self.assertEqual(immunisation_type, "covid19")

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.query = MagicMock(return_value={})

        immunisation, immunisation_type = self.repository.get_immunization_by_identifier(imms_id)
        self.assertIsNone(immunisation)
        self.assertIsNone(immunisation_type)


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
        imms = self.repository.get_immunization_by_id(imms_id)

        # Validate the results
        self.assertDictEqual(resource, imms)
        self.table.get_item.assert_called_once_with(Key={"PK": _make_immunization_pk(imms_id)})

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.table.get_item = MagicMock(return_value={})

        imms = self.repository.get_immunization_by_id(imms_id)
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

    def test_create_immunization(self):
        """it should create Immunization, and return created object"""
        imms = create_covid_19_immunization_dict(imms_id="an-id")

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, "Test")

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
        imms = create_covid_19_immunization_dict(imms_id="an-id")

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, None, "Test")

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
        imms = create_covid_19_immunization_dict("an-id")
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, "Test")

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

        imms = create_covid_19_immunization_dict(imms_id)
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        _ = self.repository.create_immunization(imms, self.patient, "Test")

        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(item["PK"].startswith("Immunization#"))
        self.assertNotEqual(item["PK"], "Immunization#original-id-from-request")

    def test_create_immunization_returns_new_id(self):
        """create should return the persisted object i.e. with new id"""
        imms_id = "original-id-from-request"
        imms = create_covid_19_immunization_dict(imms_id)
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        response = self.repository.create_immunization(imms, self.patient, "Test")

        self.assertNotEqual(response["id"], imms_id)

    def test_create_should_catch_dynamo_error(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.put_item = MagicMock(return_value=response)
        self.table.query = MagicMock(return_value={})

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.create_immunization(create_covid_19_immunization_dict("an-id"), self.patient, "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)

    def test_create_throws_error_when_identifier_already_in_dynamodb(self):
        """it should throw UnhandledResponse when trying to update an immunization with an identfier that is already stored"""
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient

        self.table.query = MagicMock(return_value={"Items": [{"Resource": '{"id": "different-id"}'}], "Count": 1})
        identifier = f"{imms['identifier'][0]['system']}#{imms['identifier'][0]['value']}"
        with self.assertRaises(IdentifierDuplicationError) as e:
            # When
            self.repository.create_immunization(imms, self.patient, "Test")

        self.assertEqual(str(e.exception), f"The provided identifier: {identifier} is duplicated")


class TestCreateImmunizationPatientIndex(TestFhirRepositoryBase):
    """create_immunization should create a patient record with vaccine type"""

    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = {"id": "a-patient-id"}

    def test_create_patient_gsi(self):
        """create Immunization method should create Patient index with nhs-number as ID and no system"""
        imms = create_covid_19_immunization_dict("an-id")

        nhs_number = "1234567890"
        imms["contained"][1]["identifier"][0]["value"] = nhs_number

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        # When
        _ = self.repository.create_immunization(imms, self.patient, "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["PatientPK"], f"Patient#{nhs_number}")

    def test_create_patient_with_vaccine_type(self):
        """Patient record should have a sort-key based on vaccine-type"""
        imms = create_covid_19_immunization_dict("an-id")

        update_target_disease_code(imms, "FLU")
        vaccine_type = get_vaccine_type(imms)

        self.table.query = MagicMock(return_value={"Count": 0})
        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})

        # When
        _ = self.repository.create_immunization(imms, self.patient, "Test")

        # Then
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertTrue(item["PatientSK"].startswith(f"{vaccine_type}#"))


class TestUpdateImmunization(TestFhirRepositoryBase):
    def setUp(self):
        super().setUp()
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.patient = _make_a_patient("update-patient-id")

    def test_update1(self):
        """it should update record by replacing both Immunization and Patient"""

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

            act_resource, updated_version = self.repository.update_immunization(imms_id, imms, self.patient, 1, "Test")

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

        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient

        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.update_item = MagicMock(return_value=response)
        self.table.query = MagicMock(return_value={})

        with self.assertRaises(UnhandledResponseError) as e:
            # When

            self.repository.update_immunization(imms_id, imms, self.patient, 1, "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)

    def test_update_throws_error_when_identifier_already_in_dynamodb(self):
        """it should throw IdentifierDuplicationError when trying to update an immunization with an identfier that is already stored"""

        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient
        identifier = f"{imms['identifier'][0]['system']}#{imms['identifier'][0]['value']}"
        self.table.query = MagicMock(return_value={"Items": [{"Resource": '{"id": "different-id"}'}], "Count": 1})

        with self.assertRaises(IdentifierDuplicationError) as e:
            # When

            self.repository.update_immunization(imms_id, imms, self.patient, 1, "Test")

        self.assertEqual(str(e.exception), f"The provided identifier: {identifier} is duplicated")

    def test_reinstate_immunization_success(self):
        """it should reinstate an immunization successfully"""
        imms_id = "reinstate-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient
        resource = {"reinstate": "ok"}
        self.table.query.return_value = {}

        self.table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": json.dumps(resource)},
        }

        with patch("time.time", return_value=123456):
            result, version = self.repository.reinstate_immunization(imms_id, imms, self.patient, 1, "Test")

        self.assertEqual(result, resource)
        self.assertEqual(version, 2)

    def test_update_reinstated_immunization_success(self):
        """it should update a reinstated immunization successfully"""
        imms_id = "reinstated-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = self.patient
        resource = {"reinstated": "ok"}
        self.table.query.return_value = {}

        self.table.update_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            "Attributes": {"Resource": json.dumps(resource)},
        }

        with patch("time.time", return_value=123456):
            result, version = self.repository.update_reinstated_immunization(imms_id, imms, self.patient, 1, "Test")

        self.assertEqual(result, resource)
        self.assertEqual(version, 2)


class TestDeleteImmunization(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.repository = ImmunizationRepository(table=self.table)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_deleted_immunization(self):
        """it should return None if Immunization is logically deleted"""
        imms_id = "a-deleted-id"
        self.table.get_item = MagicMock(return_value={"Item": {"Resource": "{}", "DeletedAt": time.time()}})

        imms = self.repository.get_immunization_by_id(imms_id)
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
            _id = self.repository.delete_immunization(imms_id, "Test")

        # Then
        self.table.update_item.assert_called_once_with(
            Key={"PK": _make_immunization_pk(imms_id)},
            UpdateExpression="SET DeletedAt = :timestamp, Operation = :operation, SupplierSystem = :supplier_system",
            ExpressionAttributeValues={":timestamp": now_epoch, ":operation": "DELETE", ":supplier_system": "Test"},
            ReturnValues=ANY,
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
        self.table.update_item = MagicMock(return_value=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.delete_immunization(imms_id, "Test")

        # Then
        self.assertDictEqual(e.exception.response, response)


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
        _ = self.repository.find_immunizations(nhs_number, vaccine_types={"COVID19"})

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
        _ = self.repository.find_immunizations("an-id", {"COVID19"})

        # Then
        self.table.query.assert_called_once_with(
            IndexName="PatientGSI", KeyConditionExpression=ANY, FilterExpression=is_
        )

    def test_map_results_to_immunizations(self):
        """it should map Resource list into a list of Immunizations"""
        imms1 = {"id": 1, "meta": {"versionId": 1}}
        imms2 = {"id": 2, "meta": {"versionId": 1}}
        items = [
            {"Resource": json.dumps(imms1), "PatientSK": "COVID19#some_other_text", "Version": "1"},
            {"Resource": json.dumps(imms2), "PatientSK": "COVID19#some_other_text", "Version": "1"},
        ]

        dynamo_response = {"ResponseMetadata": {"HTTPStatusCode": 200}, "Items": items}
        self.table.query = MagicMock(return_value=dynamo_response)

        # When
        results = self.repository.find_immunizations("an-id", {"COVID19"})

        # Then
        self.assertListEqual(results, [imms1, imms2])

    def test_bad_response_from_dynamo(self):
        """it should throw UnhandledResponse when the response from dynamodb can't be handled"""
        bad_request = 400
        response = {"ResponseMetadata": {"HTTPStatusCode": bad_request}}
        self.table.query = MagicMock(return_value=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.repository.find_immunizations("an-id", {"COVID19"})

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
        imms = create_covid_19_immunization_dict(imms_id="an-id")
        imms["doseQuantity"] = 0.7477

        self.table.put_item = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
        self.table.query = MagicMock(return_value={})

        res_imms = self.repository.create_immunization(imms, self.patient, "Test")

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
            act_resource, act_version = self.repository.update_immunization(imms_id, imms, self.patient, 1, "Test")
        self.assertDictEqual(act_resource, resource)
        self.assertEqual(act_version, 2)

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
        imms_id = "an-imms-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["doseQuantity"] = 1.5556
        updated_dose_quantity = 0.7566
        imms["doseQuantity"] = updated_dose_quantity
        imms["patient"] = self.patient
        resource = imms
        self.run_update_immunization_test(imms_id, imms, resource, updated_dose_quantity)

    def test_decimal_on_update_patient(self):
        """it should update record by replacing both Immunization and Patient and dose quantity"""
        imms_id = "an-imms-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["doseQuantity"] = 1.590
        imms["patient"] = self.patient
        resource = {"doseQuantity": 1.590, "foo": "bar"}
        self.run_update_immunization_test(imms_id, imms, resource)
