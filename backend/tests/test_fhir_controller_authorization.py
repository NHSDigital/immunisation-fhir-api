import json
import unittest
from unittest.mock import patch
import uuid
from typing import Set
from unittest.mock import create_autospec

from authorization import (
    Authorization,
    UnknownPermission,
    EndpointOperation,
    AuthType,
    Permission,
    AUTHENTICATION_HEADER,
    PERMISSIONS_HEADER,
)
from fhir_controller import FhirController
from fhir_repository import ImmunizationRepository
from fhir_service import FhirService, UpdateOutcome
from models.errors import UnauthorizedError, UnauthorizedVaxError
from tests.utils.immunization_utils import create_covid_19_immunization

"test"
def full_access(exclude: Set[Permission] = None) -> Set[Permission]:
    return {*Permission}.difference(exclude)


def make_aws_event(auth_type: AuthType, permissions=None) -> dict:
    if permissions is None:
        permissions = full_access()
    header = ",".join(permissions)

    return {"headers": {PERMISSIONS_HEADER: header, AUTHENTICATION_HEADER: str(auth_type)}}


class TestFhirControllerAuthorization(unittest.TestCase):
    """For each endpoint, we need to test three scenarios.
    1- Happy path test: make sure authorize() receives correct EndpointOperation, and we pass aws_event
    2- Unauthorized test: make sure we send a 403 OperationOutcome
    3- UnknownPermission test: make sure we send a 500 OperationOutcome
    """

    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    # EndpointOperation.READ
    def test_get_imms_by_id_authorized(self):
        aws_event = {"pathParameters": {"id": "an-id"}}

        _ = self.controller.get_immunization_by_id(aws_event)

        self.authorizer.authorize.assert_called_once_with(EndpointOperation.READ, aws_event)

    def test_get_imms_by_id_unauthorized(self):
        aws_event = {"pathParameters": {"id": "an-id"}}
        self.authorizer.authorize.side_effect = UnauthorizedError()

        response = self.controller.get_immunization_by_id(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_get_imms_by_id_unknown_permission(self):
        aws_event = {"pathParameters": {"id": "an-id"}}
        self.authorizer.authorize.side_effect = UnknownPermission()

        response = self.controller.get_immunization_by_id(aws_event)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

    # EndpointOperation.CREATE
    @patch("fhir_controller.get_supplier_permissions")
    def test_create_imms_authorized_supplier_system(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["Covid19:create"]
        aws_event = {"headers":{"SupplierSystem" : "Test"},"body": create_covid_19_immunization(str(uuid.uuid4())).json()}

        _ = self.controller.create_immunization(aws_event)

        self.authorizer.authorize.assert_called_once_with(EndpointOperation.CREATE, aws_event)

    def test_create_imms_unauthorized(self):
        aws_event = {"headers":{"SupplierSystem" : "Test"},"body": create_covid_19_immunization(str(uuid.uuid4())).json()}
        self.authorizer.authorize.side_effect = UnauthorizedError()

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_create_imms_unknown_permission(self):
        aws_event = {"headers":{"SupplierSystem" : "Test"},"body": create_covid_19_immunization(str(uuid.uuid4())).json()}
        self.authorizer.authorize.side_effect = UnknownPermission()

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

    # EndpointOperation.UPDATE
    @patch("fhir_controller.get_supplier_permissions")
    def test_update_imms_authorized(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["Covid19.CRUDS"]
        imms_id = str(uuid.uuid4())
        aws_event = {"headers": {"E-Tag":1, "SupplierSystem" : "Test"},"pathParameters": {"id": imms_id}, "body": create_covid_19_immunization(imms_id).json()}
        self.service.get_immunization_by_id_all.return_value = {"resource":"new_value","Version":2,"DeletedAt": False, "VaccineType":"COVID19"}
        self.service.update_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"

        _ = self.controller.update_immunization(aws_event)

        self.authorizer.authorize.assert_called_once_with(EndpointOperation.UPDATE, aws_event)
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_update_imms_unauthorized_vaxx_in_record(self,mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["Covid19.CRUDS"]
        imms_id = str(uuid.uuid4())
        aws_event = {"headers": {"E-Tag":1, "SupplierSystem" : "Test"},"pathParameters": {"id": imms_id}, "body": create_covid_19_immunization(imms_id).json()}
        self.service.get_immunization_by_id_all.return_value = {"resource":"new_value","Version":1,"DeletedAt": False, "VaccineType":"Flu"}
        
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")            
            
        self.authorizer.authorize.assert_called_once_with(EndpointOperation.UPDATE, aws_event)

    def test_update_imms_unauthorized(self):
        imms_id = str(uuid.uuid4())
        aws_event = {"headers": {"E-Tag":1, "SupplierSystem" : "Test"},"pathParameters": {"id": imms_id}, "body": create_covid_19_immunization(imms_id).json()}
        self.authorizer.authorize.side_effect = UnauthorizedError()

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_update_imms_unknown_permission(self):
        imms_id = str(uuid.uuid4())
        aws_event = {"headers": {"E-Tag":1, "SupplierSystem" : "Test"},"pathParameters": {"id": imms_id}, "body": create_covid_19_immunization(imms_id).json()}
        self.authorizer.authorize.side_effect = UnknownPermission()

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

    # EndpointOperation.DELETE
    @patch("fhir_controller.get_supplier_permissions")
    def test_delete_imms_authorized(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        aws_event = {"pathParameters": {"id": "an-id"},"headers": {"SupplierSystem" : "Test"}}

        _ = self.controller.delete_immunization(aws_event)

        self.authorizer.authorize.assert_called_once_with(EndpointOperation.DELETE, aws_event)

    def test_delete_imms_unauthorized(self):
        aws_event = {"pathParameters": {"id": "an-id"},"headers": {"SupplierSystem" : "Test"}}
        self.authorizer.authorize.side_effect = UnauthorizedError()

        response = self.controller.delete_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_delete_imms_unknown_permission(self):
        aws_event = {"pathParameters": {"id": "an-id"},"headers": {"SupplierSystem" : "Test"}}
        self.authorizer.authorize.side_effect = UnknownPermission()

        response = self.controller.delete_immunization(aws_event)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

    # EndpointOperation.SEARCH
    def test_search_imms_authorized(self):
        aws_event = {"pathParameters": {"id": "an-id"}}

        _ = self.controller.search_immunizations(aws_event)

        self.authorizer.authorize.assert_called_once_with(EndpointOperation.SEARCH, aws_event)

    def test_search_imms_unauthorized(self):
        aws_event = {"pathParameters": {"id": "an-id"}}
        self.authorizer.authorize.side_effect = UnauthorizedError()

        response = self.controller.search_immunizations(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_search_imms_unknown_permission(self):
        aws_event = {"pathParameters": {"id": "an-id"}}
        self.authorizer.authorize.side_effect = UnknownPermission()

        response = self.controller.search_immunizations(aws_event)

        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")