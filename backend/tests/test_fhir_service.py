import json
import os
import unittest
from copy import deepcopy
from unittest.mock import create_autospec

from fhir.resources.R4B.bundle import Bundle as FhirBundle, BundleEntry
from fhir.resources.R4B.immunization import Immunization
from fhir_repository import ImmunizationRepository
from fhir_service import FhirService, UpdateOutcome, get_service_url
from mappings import vaccination_procedure_snomed_codes
from models.errors import (
    InvalidPatientId,
    CustomValidationError,
    ResourceNotFoundError,
    InconsistentIdError,
)
from models.fhir_immunization import ImmunizationValidator
from pds_service import PdsService
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper
from .immunization_utils import (
    create_an_immunization,
    create_an_immunization_dict,
    valid_nhs_number,
)


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


class TestGetImmunization(unittest.TestCase):
    """Tests for FhirService.get_immunization_by_id"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)

    def test_get_immunization_by_id(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        self.imms_repo.get_immunization_by_id.return_value = create_an_immunization(imms_id).dict()
        self.pds_service.get_patient_details.return_value = {}

        # When
        act_imms = self.fhir_service.get_immunization_by_id(imms_id)

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(imms_id)
        self.assertEqual(act_imms.id, imms_id)

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none-existent-id"
        self.imms_repo.get_immunization_by_id.return_value = None

        # When
        act_imms = self.fhir_service.get_immunization_by_id(imms_id)

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(imms_id)
        self.assertEqual(act_imms, None)

    def test_get_immunization_by_id_patient_restricted(self):
        """it should return a filtered Immunization when patient is restricted"""
        imms_id = "restricted_id"
        with open(
            f"{os.path.dirname(os.path.abspath(__file__))}/sample_data/" + "sample_immunization_event.json",
            "r",
            encoding="utf-8",
        ) as immunization_data_file:
            immunization_data = json.load(immunization_data_file)
        with open(
            f"{os.path.dirname(os.path.abspath(__file__))}/sample_data/filtered_sample_immunization_event.json",
            "r",
            encoding="utf-8",
        ) as filtered_immunization_data_file:
            filtered_immunization = json.load(filtered_immunization_data_file)
        self.imms_repo.get_immunization_by_id.return_value = immunization_data
        patient_data = {"meta": {"security": [{"code": "R"}]}}
        self.fhir_service.pds_service.get_patient_details.return_value = patient_data

        # When
        act_res = self.fhir_service.get_immunization_by_id(imms_id)

        # Then
        self.assertEqual(act_res, Immunization.parse_obj(filtered_immunization))


class TestCreateImmunization(unittest.TestCase):
    """Tests for FhirService.create_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)
        self.pre_validate_fhir_service = FhirService(
            self.imms_repo, self.pds_service, ImmunizationValidator(add_post_validators=False)
        )

    def test_create_immunization(self):
        """it should create Immunization and validate it"""
        imms_id = "an-id"
        self.imms_repo.create_immunization.return_value = create_an_immunization_dict(imms_id)
        pds_patient = {"id": "a-patient-id"}
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = valid_nhs_number
        req_imms = create_an_immunization_dict(imms_id, nhs_number)

        # When
        stored_imms = self.fhir_service.create_immunization(req_imms)

        # Then
        self.imms_repo.create_immunization.assert_called_once_with(req_imms, pds_patient)
        self.validator.validate.assert_called_once_with(req_imms)
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(nhs_number)
        self.assertIsInstance(stored_imms, Immunization)

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms = create_an_immunization_dict("an-id", "12345")
        expected_msg = (
            "contained[?(@.resourceType=='Patient')].identifier[0].value must be 10 characters (type=value_error)"
        )

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(imms)

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        """it should throw exception if Immunization is not valid"""

        valid_imms = create_an_immunization_dict("an-id", valid_nhs_number)

        bad_procedure_code_imms = deepcopy(valid_imms)
        bad_procedure_code_imms["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = "bad-code"
        bad_procedure_code_msg = (
            "extension[?(@.url=="
            + "'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')"
            + "].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code: "
            + "bad-code is not a valid code for this service (type=value_error)"
        )

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"

        bad_na_imms = deepcopy(valid_imms)
        bad_na_imms["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = "mockFLUcode1"
        bad_na_msg = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='IpAddress')].answer[0].valueString must not be provided for this vaccine type"
        )
        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Create
        # Invalid procedure_code
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_procedure_code_imms)

        self.assertTrue(bad_procedure_code_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_patient_name_imms)

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Not Applicable field present
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_na_imms)

        self.assertTrue(bad_na_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_an_immunization_dict("an-id", invalid_nhs_number)

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.create_immunization(bad_patient_imms)

        # Then
        self.assertEqual(e.exception.nhs_number, invalid_nhs_number)
        self.imms_repo.create_immunization.assert_not_called()


class TestUpdateImmunization(unittest.TestCase):
    """Tests for FhirService.update_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)

    def test_update_immunization(self):
        """it should update Immunization and validate NHS number"""
        imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = create_an_immunization_dict(imms_id)
        pds_patient = {"id": "a-patient-id"}
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = valid_nhs_number
        req_imms = create_an_immunization_dict(imms_id, nhs_number)

        # When
        outcome, _ = self.fhir_service.update_immunization(imms_id, req_imms)

        # Then
        self.assertEqual(outcome, UpdateOutcome.UPDATE)
        self.imms_repo.update_immunization.assert_called_once_with(imms_id, req_imms, pds_patient)
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(nhs_number)

    def test_none_existing_imms(self):
        """it should create a new record, if it doesn't exist"""
        imms_id = "an-id"
        imms = create_an_immunization_dict(imms_id, valid_nhs_number)

        self.imms_repo.update_immunization.side_effect = ResourceNotFoundError("Immunization", imms_id)
        self.imms_repo.create_immunization.return_value = create_an_immunization_dict(imms_id)
        self.fhir_service.pds_service.get_patient_details.return_value = {"id": "a-patient-id"}

        # When
        outcome, _ = self.fhir_service.update_immunization(imms_id, imms)

        # Then
        self.assertEqual(outcome, UpdateOutcome.CREATE)
        self.imms_repo.create_immunization.assert_called_once()

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms_id = "an-id"
        imms = create_an_immunization_dict(imms_id)
        imms["patient"] = {"identifier": {"value": valid_nhs_number}}

        self.imms_repo.update_immunization.return_value = {}

        validation_error = ValidationError([ErrorWrapper(TypeError('bad type'), '/type'), ], Immunization)
        self.validator.validate.side_effect = validation_error
        expected_msg = str(validation_error)

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.update_immunization("an-id", imms)

        # Then
        self.assertEqual(error.exception.message, expected_msg)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        valid_imms = create_an_immunization_dict("an-id", valid_nhs_number)

        bad_procedure_code_imms = deepcopy(valid_imms)
        bad_procedure_code_imms["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = "bad-code"
        bad_procedure_code_msg = (
            "extension[?(@.url=="
            + "'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')"
            + "].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code: "
            + "bad-code is not a valid code for this service (type=value_error)"
        )

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"

        bad_na_imms = deepcopy(valid_imms)
        bad_na_imms["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = "mockFLUcode1"
        bad_na_msg = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='IpAddress')].answer[0].valueString must not be provided for this vaccine type"
        )
        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Invalid procedure_code
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.update_immunization("an-id", bad_procedure_code_imms)

        self.assertTrue(bad_procedure_code_msg in error.exception.message)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.update_immunization("an-id", bad_patient_name_imms)

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Not Applicable field present
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.update_immunization("an-id", bad_na_imms)

        self.assertTrue(bad_na_msg in error.exception.message)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_id_not_present(self):
        """it should populate id in the message if it is not present"""
        req_imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = create_an_immunization_dict(req_imms_id)
        self.fhir_service.pds_service.get_patient_details.return_value = {"id": "patient-id"}

        req_imms = create_an_immunization_dict("we-will-remove-this-id")
        del req_imms["id"]

        # When
        self.fhir_service.update_immunization(req_imms_id, req_imms)

        # Then
        passed_imms = self.imms_repo.update_immunization.call_args.args[1]
        self.assertEqual(passed_imms["id"], req_imms_id)

    def test_consistent_imms_id(self):
        """Immunization[id] should be the same as request"""
        req_imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = None
        self.fhir_service.pds_service.get_patient_details.return_value = {"id": "patient-id"}

        obj_imms_id = "a-diff-id"
        req_imms = create_an_immunization_dict(obj_imms_id)

        with self.assertRaises(InconsistentIdError) as error:
            # When
            self.fhir_service.update_immunization(req_imms_id, req_imms)

        # Then
        self.assertEqual(req_imms_id, error.exception.imms_id)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        imms_id = "an-id"
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_an_immunization_dict(imms_id, invalid_nhs_number)

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.update_immunization(imms_id, bad_patient_imms)

        # Then
        self.assertEqual(e.exception.nhs_number, invalid_nhs_number)
        self.imms_repo.update_immunization.assert_not_called()


class TestDeleteImmunization(unittest.TestCase):
    """Tests for FhirService.delete_immunization"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)

    def test_delete_immunization(self):
        """it should delete Immunization record"""
        imms_id = "an-id"
        imms = json.loads(create_an_immunization(imms_id).json())
        self.imms_repo.delete_immunization.return_value = imms

        # When
        act_imms = self.fhir_service.delete_immunization(imms_id)

        # Then
        self.imms_repo.delete_immunization.assert_called_once_with(imms_id)
        self.assertIsInstance(act_imms, Immunization)
        self.assertEqual(act_imms.id, imms_id)


class TestSearchImmunizations(unittest.TestCase):
    """Tests for FhirService.search_immunizations"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)
        self.nhsSearchParam = "-nhsNumber"
        self.diseaseTypeSearchParam = "-diseaseType"

    def test_map_disease_type_to_disease_code(self):
        """it should map disease_type to disease_code"""
        # TODO: for this ticket we are assuming code is provided
        nhs_number = "9990548609"
        disease_type = "1324681000000101"
        params = f"{self.nhsSearchParam}={nhs_number}&{self.diseaseTypeSearchParam}={disease_type}"

        disease_code = vaccination_procedure_snomed_codes[disease_type]
        # When
        _ = self.fhir_service.search_immunizations(nhs_number, disease_code, params)

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(nhs_number, disease_code)

    def test_make_fhir_bundle_from_search_result(self):
        """it should return a FHIR:List[Immunization] resource"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_an_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = "9990548609"
        disease_type = "a-code"
        params = f"{self.nhsSearchParam}={nhs_number}&{self.diseaseTypeSearchParam}={disease_type}"
        # When
        result = self.fhir_service.search_immunizations(nhs_number, disease_type, params)
        # Then
        self.assertIsInstance(result, FhirBundle)
        self.assertEqual(result.type, "searchset")
        self.assertEqual(len(result.entry), len(imms_ids))
        # Assert each entry in the bundle
        for i, entry in enumerate(result.entry):
            self.assertIsInstance(entry, BundleEntry)
            self.assertEqual(entry.resource.resource_type, "Immunization")
            self.assertEqual(entry.resource.id, imms_ids[i])
        # Assert self link
        self.assertEqual(len(result.link), 1)  # Assert that there is only one link
        self.assertEqual(result.link[0].relation, "self")
