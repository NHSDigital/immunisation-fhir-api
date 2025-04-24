import unittest
import uuid
from unittest.mock import Mock, create_autospec
from tests.utils.immunization_utils import create_covid_19_immunization
from fhir_batch_service import ImmunizationBatchService
from fhir_batch_repository import ImmunizationBatchRepository
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    CustomValidationError,
    IdentifierDuplicationError,
)
from fhir_batch_controller import ImmunizationBatchController


class TestCreateImmunizationBatchController(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_service = create_autospec(ImmunizationBatchService)
        self.mock_table = Mock()
        self.controller = ImmunizationBatchController(
            immunization_repo=self.mock_repo, fhir_service=self.mock_service
        )

    def test_send_request_to_dynamo_create_success(self):
        """it should create Immunization and return imms id location"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "CREATE",
        }

        self.mock_service.create_immunization.return_value = imms_id

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, imms_id)
        self.mock_service.create_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_create_badrequest(self):
        """it should return error since it got failed in initial validation"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        create_result = CustomValidationError(
            message="Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        )

        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "CREATE",
        }

        self.mock_service.create_immunization.return_value = create_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, create_result)
        self.mock_service.create_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_create_duplicate(self):
        """it should not create the Immunization since its a duplicate record"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        create_result = IdentifierDuplicationError(identifier="test#123")
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "CREATE",
        }

        self.mock_service.create_immunization.return_value = create_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, create_result)
        self.mock_service.create_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_create_unhandled_error(self):
        """it should not create the Immunization since the error occoured in db"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = UnhandledResponseError(
            response="Non-200 response from dynamodb", message="connection timeout"
        )
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "CREATE",
        }

        self.mock_service.create_immunization.return_value = UnhandledResponseError(
            "Non-200 response from dynamodb", "connection timeout"
        )

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.create_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )


class TestUpdateImmunizationBatchController(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_service = create_autospec(ImmunizationBatchService)
        self.mock_table = Mock()
        self.controller = ImmunizationBatchController(
            immunization_repo=self.mock_repo, fhir_service=self.mock_service
        )

    def test_send_request_to_dynamo_update_success(self):
        """it should update Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "UPDATE",
        }

        self.mock_service.update_immunization.return_value = imms_id

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, imms_id)
        self.mock_service.update_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_update_badrequest(self):
        """it should return error since it got failed in initial validation"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = CustomValidationError(
            message="Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        )
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "UPDATE",
        }

        self.mock_service.update_immunization.return_value = update_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.update_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_update_resource_not_found(self):
        """it should not update the Immunization since no resource found for the record"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = ResourceNotFoundError("Immunization", "test#123")
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "UPDATE",
        }

        self.mock_service.update_immunization.return_value = update_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.update_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_update_unhandled_error(self):
        """it should not update the Immunization since the error occoured in db"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = UnhandledResponseError(
            response="Non-200 response from dynamodb", message="connection timeout"
        )
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "UPDATE",
        }

        self.mock_service.update_immunization.return_value = UnhandledResponseError(
            "Non-200 response from dynamodb", "connection timeout"
        )

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.update_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )


class TestDeleteImmunizationBatchController(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_service = create_autospec(ImmunizationBatchService)
        self.mock_table = Mock()
        self.controller = ImmunizationBatchController(
            immunization_repo=self.mock_repo, fhir_service=self.mock_service
        )

    def test_send_request_to_dynamo_delete_success(self):
        """it should delete Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "DELETE",
        }

        self.mock_service.delete_immunization.return_value = imms_id

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, imms_id)
        self.mock_service.delete_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_delete_badrequest(self):
        """it should return error since it got failed in initial validation"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = CustomValidationError(
            message="Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        )
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "DELETE",
        }

        self.mock_service.delete_immunization.return_value = update_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.delete_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_delete_resource_not_found(self):
        """it should not delete the Immunization since no resource found for the record"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = ResourceNotFoundError("Immunization", "test#123")
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "DELETE",
        }

        self.mock_service.delete_immunization.return_value = update_result

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.delete_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )

    def test_send_request_to_dynamo_delete_unhandled_error(self):
        """it should not delete the Immunization since the error occoured in db"""

        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        update_result = UnhandledResponseError(
            response="Non-200 response from dynamodb", message="connection timeout"
        )
        message_body = {
            "supplier": "test_supplier",
            "fhir_json": imms.json(),
            "vax_type": "test_vax",
            "operation_requested": "DELETE",
        }

        self.mock_service.delete_immunization.return_value = UnhandledResponseError(
            "Non-200 response from dynamodb", "connection timeout"
        )

        result = self.controller.send_request_to_dynamo(
            message_body, self.mock_table, True
        )

        self.assertEqual(result, update_result)
        self.mock_service.delete_immunization.assert_called_once_with(
            immunization=message_body["fhir_json"],
            supplier_system=message_body["supplier"],
            vax_type=message_body["vax_type"],
            table=self.mock_table,
            is_present=True,
        )


if __name__ == "__main__":
    unittest.main()
