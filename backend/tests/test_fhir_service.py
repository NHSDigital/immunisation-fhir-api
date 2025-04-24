import json
import uuid
import datetime
import unittest
from copy import deepcopy
from unittest.mock import create_autospec
from decimal import Decimal

from fhir.resources.R4B.bundle import Bundle as FhirBundle, BundleEntry
from fhir.resources.R4B.immunization import Immunization
from fhir_repository import ImmunizationRepository
from fhir_service import FhirService, UpdateOutcome, get_service_url
from mappings import VaccineTypes
from models.errors import InvalidPatientId, CustomValidationError
from models.fhir_immunization import ImmunizationValidator
from pds_service import PdsService
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper
from tests.utils.immunization_utils import (
    create_covid_19_immunization,
    create_covid_19_immunization_dict,
    create_covid_19_immunization_dict_no_id,
    VALID_NHS_NUMBER,
)
from .utils.generic_utils import load_json_data
from src.constants import NHS_NUMBER_USED_IN_SAMPLE_DATA

"test"


class TestServiceUrl(unittest.TestCase):
    def test_get_service_url(self):
        """it should create service url"""
        env = "int"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://{env}.api.service.nhs.uk/{base_path}")
        # default should be internal-dev
        env = "it-does-not-exist"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")
        # prod should not have a subdomain
        env = "prod"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://api.service.nhs.uk/{base_path}")
        # any other env should fall back to internal-dev (like pr-xx or per-user)
        env = "pr-42"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")


class TestGetImmunizationByAll(unittest.TestCase):
    """Tests for FhirService.get_immunization_by_id"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )

    def test_get_immunization_by_id_by_all(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        self.imms_repo.get_immunization_by_id_all.return_value = {
            "Resource": create_covid_19_immunization(imms_id).dict()
        }

        # When
        service_resp = self.fhir_service.get_immunization_by_id_all(
            imms_id, create_covid_19_immunization(imms_id).dict()
        )
        act_imms = service_resp["Resource"]

        # Then
        self.imms_repo.get_immunization_by_id_all.assert_called_once_with(
            imms_id, create_covid_19_immunization(imms_id).dict()
        )

        self.assertEqual(act_imms["id"], imms_id)

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none-existent-id"
        self.imms_repo.get_immunization_by_id_all.return_value = None

        # When
        act_imms = self.fhir_service.get_immunization_by_id_all(
            imms_id, create_covid_19_immunization(imms_id).dict()
        )

        # Then
        self.imms_repo.get_immunization_by_id_all.assert_called_once_with(
            imms_id, create_covid_19_immunization(imms_id).dict()
        )
        self.assertEqual(act_imms, None)

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = {"identifier": {"value": VALID_NHS_NUMBER}}

        self.imms_repo.get_immunization_by_id_all.return_value = {}

        validation_error = ValidationError(
            [
                ErrorWrapper(TypeError("bad type"), "/type"),
            ],
            Immunization,
        )
        self.validator.validate.side_effect = validation_error
        expected_msg = str(validation_error)

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.get_immunization_by_id_all("an-id", imms)

        # Then
        self.assertEqual(error.exception.message, expected_msg)
        self.imms_repo.update_immunization.assert_not_called()

    def test_post_validation_failed(self):
        valid_imms = create_covid_19_immunization_dict("an-id", VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0][
            "code"
        ] = "bad-code"
        bad_target_disease_msg = (
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')]"
            + ".code - ['bad-code'] is not a valid combination of disease codes for this service"
        )

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = (
            "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"
        )

        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Invalid target_disease
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_target_disease_imms)

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_patient_name_imms)

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()


class TestGetImmunization(unittest.TestCase):
    """Tests for FhirService.get_immunization_by_id"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )

    def test_get_immunization_by_id(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        self.imms_repo.get_immunization_by_id.return_value = {
            "Resource": create_covid_19_immunization(imms_id).dict()
        }
        self.pds_service.get_patient_details.return_value = {
            "meta": {"security": [{"code": "U"}]}
        }

        # When
        service_resp = self.fhir_service.get_immunization_by_id(imms_id, "COVID19:read")
        act_imms = service_resp["Resource"]

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(
            imms_id, "COVID19:read"
        )

        self.assertEqual(act_imms.id, imms_id)

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none-existent-id"
        self.imms_repo.get_immunization_by_id.return_value = None

        # When
        act_imms = self.fhir_service.get_immunization_by_id(imms_id, "COVID19:read")

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(
            imms_id, "COVID19:read"
        )
        self.assertEqual(act_imms, None)

    def test_get_immunization_by_id_patient_not_restricted(self):
        """
        Test that get_immunization_by_id returns a FHIR Immunization Resource which has been filtered for read
        when patient is not restricted
        """
        imms_id = "non_restricted_id"

        immunization_data = load_json_data("completed_covid19_immunization_event.json")
        self.imms_repo.get_immunization_by_id.return_value = {
            "Resource": immunization_data
        }
        self.fhir_service.pds_service.get_patient_details.return_value = {
            "meta": {"security": [{"code": "U"}]}
        }

        expected_imms = load_json_data(
            "completed_covid19_immunization_event_for_read.json"
        )
        expected_output = Immunization.parse_obj(expected_imms)

        # When
        actual_output = self.fhir_service.get_immunization_by_id(
            imms_id, "COVID19:read"
        )

        # Then
        self.assertEqual(actual_output["Resource"], expected_output)

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms_id = "an-id"
        imms = create_covid_19_immunization_dict(imms_id)
        imms["patient"] = {"identifier": {"value": VALID_NHS_NUMBER}}

        self.imms_repo.get_immunization_by_id_all.return_value = {}

        validation_error = ValidationError(
            [
                ErrorWrapper(TypeError("bad type"), "/type"),
            ],
            Immunization,
        )
        self.validator.validate.side_effect = validation_error
        expected_msg = str(validation_error)

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.get_immunization_by_id_all("an-id", imms)

        # Then
        self.assertEqual(error.exception.message, expected_msg)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        valid_imms = create_covid_19_immunization_dict("an-id", VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0][
            "code"
        ] = "bad-code"
        bad_target_disease_msg = (
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"
            + " - ['bad-code'] is not a valid combination of disease codes for this service"
        )

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = (
            "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"
        )

        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Invalid target_disease
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_target_disease_imms)

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_patient_name_imms)

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()


class TestGetImmunizationIdentifier(unittest.TestCase):
    """Tests for FhirService.get_immunization_by_id"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )

    def test_get_immunization_by_identifier(self):
        """it should find an Immunization by id"""
        imms = "an-id#an-id"
        identifier = "test"
        element = "id,mEta,DDD"
        self.imms_repo.get_immunization_by_identifier.return_value = {}
        self.pds_service.get_patient_details.return_value = {}

        # When
        service_resp = self.fhir_service.get_immunization_by_identifier(
            imms, "COVID19:search", identifier, element, False
        )
        act_imms = service_resp

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(
            imms, "COVID19:search", False
        )

        self.assertEqual(act_imms["resourceType"], "Bundle")

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none"
        identifier = "test"
        element = "id"
        self.imms_repo.get_immunization_by_identifier.return_value = None

        # When
        act_imms = self.fhir_service.get_immunization_by_identifier(
            imms_id, "COVID19:search", identifier, element, False
        )

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(
            imms_id, "COVID19:search", False
        )

        self.assertEqual(act_imms["entry"], [])


class TestCreateImmunization(unittest.TestCase):
    """Tests for FhirService.create_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )
        self.pre_validate_fhir_service = FhirService(
            self.imms_repo,
            self.pds_service,
            ImmunizationValidator(add_post_validators=False),
        )

    def test_create_immunization(self):
        """it should create Immunization and validate it"""
        imms_id = "an-id"
        self.imms_repo.create_immunization.return_value = (
            create_covid_19_immunization_dict_no_id()
        )
        pds_patient = {
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}
            ]
        }
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict_no_id(nhs_number)

        # When
        stored_imms = self.fhir_service.create_immunization(
            req_imms, "COVID19:create", "Test", False
        )

        # Then
        self.imms_repo.create_immunization.assert_called_once_with(
            req_imms, pds_patient, "COVID19:create", "Test", False
        )

        self.validator.validate.assert_called_once_with(req_imms)
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(
            nhs_number
        )
        self.assertIsInstance(stored_imms, Immunization)

    def test_create_immunization_batch(self):
        """it should create Immunization and validate it"""
        self.imms_repo.create_immunization.return_value = (
            create_covid_19_immunization_dict_no_id()
        )
        pds_patient = {
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}
            ]
        }
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict_no_id(nhs_number)

        # When
        stored_imms = self.fhir_service.create_immunization(
            req_imms, None, "Test", True
        )

        # Then
        self.imms_repo.create_immunization.assert_called_once_with(
            req_imms, None, None, "Test", True
        )

        self.validator.validate.assert_called_once_with(req_imms)
        self.fhir_service.pds_service.get_patient_details.assert_not_called
        self.assertIsInstance(stored_imms, Immunization)

    def test_create_immunization_with_id(self):
        """it should throw exception if id present in create Immunization"""
        imms = create_covid_19_immunization_dict("an-id", "9990548609")
        expected_msg = "id field must not be present for CREATE operation"

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(
                imms, "COVID19:create", "Test", False
            )

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms = create_covid_19_immunization_dict_no_id("9990548609")
        imms["lotNumber"] = 1234
        expected_msg = "lotNumber must be a string"

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(
                imms, "COVID19:create", "Test", False
            )

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        """it should throw exception if Immunization is not valid"""

        valid_imms = create_covid_19_immunization_dict_no_id(VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0][
            "code"
        ] = "bad-code"
        bad_target_disease_msg = (
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')]"
            + ".code - ['bad-code'] is not a valid combination of disease codes for this service"
        )

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = (
            "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"
        )

        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Create
        # Invalid target_disease
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(
                bad_target_disease_imms, "COVID19:create", "Test", False
            )

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(
                bad_patient_name_imms, "COVID19:create", "Test", False
            )

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_covid_19_immunization_dict_no_id(invalid_nhs_number)

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.create_immunization(
                bad_patient_imms, "COVID19:create", "Test", False
            )

        # Then
        self.assertEqual(e.exception.patient_identifier, invalid_nhs_number)
        self.imms_repo.create_immunization.assert_not_called()


class TestUpdateImmunization(unittest.TestCase):
    """Tests for FhirService.update_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )

    def test_update_immunization(self):
        """it should update Immunization and validate NHS number"""
        imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = (
            create_covid_19_immunization_dict(imms_id)
        )
        pds_patient = {
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}
            ]
        }
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict(imms_id, nhs_number)

        # When
        outcome, _ = self.fhir_service.update_immunization(
            imms_id, req_imms, 1, "COVID19:update", "Test", False
        )

        # Then
        self.assertEqual(outcome, UpdateOutcome.UPDATE)
        self.imms_repo.update_immunization.assert_called_once_with(
            imms_id, req_imms, pds_patient, 1, "COVID19:update", "Test", False
        )
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(
            nhs_number
        )

    def test_update_immunization_batch(self):
        """it should update Immunization and validate NHS number"""
        imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = (
            create_covid_19_immunization_dict(imms_id)
        )
        pds_patient = {
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}
            ]
        }
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict(imms_id, nhs_number)

        # When
        outcome, _ = self.fhir_service.update_immunization(
            imms_id, req_imms, 1, None, "Test", True
        )

        # Then
        self.assertEqual(outcome, UpdateOutcome.UPDATE)
        self.imms_repo.update_immunization.assert_called_once_with(
            imms_id, req_imms, None, 1, None, "Test", True
        )
        self.fhir_service.pds_service.get_patient_details.assert_not_called()

    def test_id_not_present(self):
        """it should populate id in the message if it is not present"""
        req_imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = (
            create_covid_19_immunization_dict(req_imms_id)
        )
        self.fhir_service.pds_service.get_patient_details.return_value = {
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}
            ]
        }

        req_imms = create_covid_19_immunization_dict("we-will-remove-this-id")
        del req_imms["id"]

        # When
        self.fhir_service.update_immunization(
            req_imms_id, req_imms, 1, "COVID19:update", "Test", False
        )

        # Then
        passed_imms = self.imms_repo.update_immunization.call_args.args[1]
        self.assertEqual(passed_imms["id"], req_imms_id)

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        imms_id = "an-id"
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_covid_19_immunization_dict(
            imms_id, invalid_nhs_number
        )

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.update_immunization(
                imms_id, bad_patient_imms, 1, "COVID19:update", "Test", False
            )

        # Then
        self.assertEqual(e.exception.patient_identifier, invalid_nhs_number)
        self.imms_repo.update_immunization.assert_not_called()


class TestDeleteImmunization(unittest.TestCase):
    """Tests for FhirService.delete_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )

    def test_delete_immunization(self):
        """it should delete Immunization record"""
        imms_id = "an-id"
        imms = json.loads(create_covid_19_immunization(imms_id).json())
        self.imms_repo.delete_immunization.return_value = imms

        # When
        act_imms = self.fhir_service.delete_immunization(
            imms_id, "COVID:delete", "Test", False
        )

        # Then
        self.imms_repo.delete_immunization.assert_called_once_with(
            imms_id, "COVID:delete", "Test", False
        )
        self.assertIsInstance(act_imms, Immunization)
        self.assertEqual(act_imms.id, imms_id)

    def test_delete_immunization_for_batch(self):
        """it should delete Immunization record"""
        imms_id = "an-id"
        imms = json.loads(create_covid_19_immunization(imms_id).json())
        self.imms_repo.delete_immunization.return_value = imms

        # When
        act_imms = self.fhir_service.delete_immunization(imms_id, None, "Test", True)

        # Then
        self.imms_repo.delete_immunization.assert_called_once_with(
            imms_id, None, "Test", True
        )
        self.assertIsInstance(act_imms, Immunization)
        self.assertEqual(act_imms.id, imms_id)


class TestSearchImmunizations(unittest.TestCase):
    """Tests for FhirService.search_immunizations"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(
            self.imms_repo, self.pds_service, self.validator
        )
        self.nhs_search_param = "patient.identifier"
        self.vaccine_type_search_param = "-immunization.target"
        self.sample_patient_resource = load_json_data("bundle_patient_resource.json")

    def test_vaccine_type_search(self):
        """It should search for the correct vaccine type"""
        nhs_number = VALID_NHS_NUMBER
        vaccine_type = VaccineTypes.covid_19
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_type}"

        # When
        _ = self.fhir_service.search_immunizations(nhs_number, [vaccine_type], params)

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(
            nhs_number, [vaccine_type]
        )

    def test_make_fhir_bundle_from_search_result(self):
        """It should return a FHIR Bundle resource"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_types}"
        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, params
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]
        # Then
        self.assertIsInstance(result, FhirBundle)
        self.assertEqual(result.type, "searchset")
        self.assertEqual(len(imms_ids), len(searched_imms))
        # Assert each entry in the bundle
        for i, entry in enumerate(searched_imms):
            self.assertIsInstance(entry, BundleEntry)
            self.assertEqual(entry.resource.resource_type, "Immunization")
            self.assertEqual(entry.resource.id, imms_ids[i])
        # Assert self link
        self.assertEqual(len(result.link), 1)
        self.assertEqual(result.link[0].relation, "self")

    def test_date_from_is_used_to_filter(self):
        """It should return only Immunizations after date_from"""
        # Arrange
        imms = [
            ("imms-1", "2021-02-07T13:28:17.271+00:00"),
            ("imms-2", "2021-02-08T13:28:17.271+00:00"),
        ]
        imms_list = [
            create_covid_19_immunization_dict(
                imms_id, occurrence_date_time=occcurrence_date_time
            )
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # CASE: Day before.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 6)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # CASE:Day of first, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 7)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # CASE: Day of second, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 8)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(1, len(searched_imms))
        self.assertEqual(imms_ids[1], searched_imms[0].resource.id)

        # CASE: Day after.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 9)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(0, len(searched_imms))

    def test_date_from_is_optional(self):
        """It should return everything when no date_from is specified"""
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # CASE: Without date_from
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: With date_from
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 3, 6)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_date_to_is_used_to_filter(self):
        """It should return only Immunizations before date_to"""
        # Arrange
        imms = [
            ("imms-1", "2021-02-07T13:28:17.271+00:00"),
            ("imms-2", "2021-02-08T13:28:17.271+00:00"),
        ]
        imms_list = [
            create_covid_19_immunization_dict(
                imms_id, occurrence_date_time=occcurrence_date_time
            )
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # CASE: Day after.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 9)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: Day of second, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 8)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: Day of first, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 7)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(len(searched_imms), 1)
        self.assertEqual(searched_imms[0].resource.id, imms_ids[0])

        # CASE: Day before.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 6)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        self.assertEqual(len(searched_imms), 0)

    def test_date_to_is_optional(self):
        """It should return everything when no date_to is specified"""
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # CASE 1: Without date_to argument
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE 2: With date_to argument
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 3, 8)
        )
        searched_imms = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_immunization_resources_are_filtered_for_search(self):
        """
        Test that each immunization resource returned is filtered to include only the appropriate fields for a search
        response when the patient is Unrestricted
        """
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [
            create_covid_19_immunization_dict(
                imms_id,
                NHS_NUMBER_USED_IN_SAMPLE_DATA,
                occurrence_date_time="2021-02-07T13:28:17+00:00",
            )
            for imms_id in imms_ids
        ]

        vaccine_types = [VaccineTypes.covid_19]
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result = self.fhir_service.search_immunizations(
            NHS_NUMBER_USED_IN_SAMPLE_DATA, vaccine_types, ""
        )
        searched_imms = [
            json.loads(entry.json(), parse_float=Decimal)
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]
        searched_patient = [
            json.loads(entry.json())
            for entry in result.entry
            if entry.resource.resource_type == "Patient"
        ][0]

        # Then
        expected_output_resource = load_json_data(
            "completed_covid19_immunization_event_filtered_for_search_using_bundle_patient_resource.json"
        )
        expected_output_resource["patient"]["reference"] = searched_patient["fullUrl"]

        for i, entry in enumerate(searched_imms):
            # Check that entry has correct resource id
            self.assertEqual(entry["resource"]["id"], imms_ids[i])

            # Check that output is as expected (filtered, with id added)
            expected_output_resource["id"] = imms_ids[i]
            self.assertEqual(entry["resource"], expected_output_resource)

    def test_matches_contain_fullUrl(self):
        """All matches must have a fullUrl consisting of their id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        entries = [
            entry
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]

        # Then
        for i, entry in enumerate(entries):
            self.assertEqual(
                entry.fullUrl,
                f"https://api.service.nhs.uk/immunisation-fhir-api/Immunization/{imms_ids[i]}",
            )

    def test_patient_contains_fullUrl(self):
        """Patient must have a fullUrl consisting of its id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {
            **deepcopy(self.sample_patient_resource),
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next(
            (
                entry
                for entry in result.entry
                if entry.resource.resource_type == "Patient"
            ),
            None,
        )
        patient_full_url = patient_entry.fullUrl
        self.assertTrue(patient_full_url.startswith("urn:uuid:"))

        # Check that final part of fullUrl is a uuid
        patient_full_url_uuid = patient_full_url.split(":")[2]
        self.assertTrue(uuid.UUID(patient_full_url_uuid))

    def test_patient_included(self):
        """Patient is included in the results."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        patient = next(
            contained
            for contained in imms_list[0]["contained"]
            if contained["resourceType"] == "Patient"
        )
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {
            **patient,
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next(
            (
                entry
                for entry in result.entry
                if entry.resource.resource_type == "Patient"
            )
        )
        self.assertIsNotNone(patient_entry)

    def test_patient_is_stripped(self):
        """The included Patient is a subset of the data."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        patient = next(
            contained
            for contained in imms_list[0]["contained"]
            if contained["resourceType"] == "Patient"
        )
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {
            **patient,
            "meta": {"security": [{"code": "U"}]},
        }
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next(
            (
                entry
                for entry in result.entry
                if entry.resource.resource_type == "Patient"
            )
        )
        patient_entry_resource = patient_entry.resource
        fields_to_keep = ["id", "resource_type", "identifier"]
        # self.assertListEqual(sorted(vars(patient_entry.resource).keys()), sorted(fields_to_keep))
        # self.assertGreater(len(patient), len(fields_to_keep))
        for field in fields_to_keep:
            self.assertTrue(
                hasattr(patient_entry_resource, field), f"{field} in Patient"
            )
            self.assertIsNotNone(getattr(patient_entry_resource, field))

        for k, v in vars(patient_entry_resource).items():
            if k not in fields_to_keep:
                self.assertIsNone(v)
