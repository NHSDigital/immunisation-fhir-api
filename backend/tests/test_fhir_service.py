import json
import datetime
import os
import unittest
from copy import deepcopy
from unittest.mock import create_autospec

from fhir.resources.R4B.bundle import Bundle as FhirBundle, BundleEntry
from fhir.resources.R4B.immunization import Immunization
from fhir_repository import ImmunizationRepository
from fhir_service import FhirService, UpdateOutcome, get_service_url
from mappings import VaccineTypes
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
from tests.immunization_utils import (
    create_covid_19_immunization,
    create_covid_19_immunization_dict,
    VALID_NHS_NUMBER,
)
from src.mappings import DiseaseCodes
from .utils.generic_utils import load_json_data


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
        self.imms_repo.get_immunization_by_id.return_value = {"Resource": create_covid_19_immunization(imms_id).dict()}
        self.pds_service.get_patient_details.return_value = {}

        # When
        service_resp = self.fhir_service.get_immunization_by_id(imms_id,"COVID19:read")
        act_imms = service_resp["Resource"]

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:read")
        
        self.assertEqual(act_imms.id, imms_id)

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none-existent-id"
        self.imms_repo.get_immunization_by_id.return_value = None

        # When
        act_imms = self.fhir_service.get_immunization_by_id(imms_id,"COVID19:read")

        # Then
        self.imms_repo.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:read")
        self.assertEqual(act_imms, None)

    def test_get_immunization_by_id_patient_not_restricted(self):
        """
        Test that get_immunization_by_id returns a FHIR Immunization Resource which has been filtered for read,
        but not for s-flag, when patient is not restricted
        """
        imms_id = "non_restricted_id"

        immunization_data = load_json_data("completed_covid19_immunization_event.json")
        self.imms_repo.get_immunization_by_id.return_value = {"Resource": immunization_data}
        self.fhir_service.pds_service.get_patient_details.return_value = {"meta": {}}

        expected_imms = load_json_data("completed_covid19_immunization_event_filtered_for_read.json")
        expected_output = Immunization.parse_obj(expected_imms)

        # When
        actual_output = self.fhir_service.get_immunization_by_id(imms_id,"COVID19:read")

        # Then
        self.assertEqual(actual_output["Resource"], expected_output)

    def test_get_immunization_by_id_patient_restricted(self):
        """it should return a filtered Immunization when patient is restricted """
        imms_id = "restricted_id"
        immunization_data = load_json_data("completed_covid19_immunization_event.json")
        filtered_immunization = load_json_data("completed_covid19_immunization_event_filtered_for_s_flag_and_read.json")
        self.imms_repo.get_immunization_by_id.return_value = {"Resource": immunization_data}
        patient_data = {"meta": {"security": [{"code": "R"}]}}
        self.fhir_service.pds_service.get_patient_details.return_value = patient_data

        # When
        resp_imms = self.fhir_service.get_immunization_by_id(imms_id, "COVID19:read")
        act_res =resp_imms["Resource"]
        filtered_immunization_res=Immunization.parse_obj(filtered_immunization)
        # Then
        self.assertEqual(act_res, filtered_immunization_res)

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
            self.fhir_service.get_immunization_by_id_all("an-id", imms,'test')

        # Then
        self.assertEqual(error.exception.message, expected_msg)
        self.imms_repo.update_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        valid_imms = create_covid_19_immunization_dict("an-id", VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        bad_target_disease_msg = "['bad-code'] is not a valid combination of disease codes for this service"

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"

        bad_na_imms = deepcopy(valid_imms)
        bad_na_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = DiseaseCodes.flu
        bad_na_msg = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='IpAddress')].answer[0].valueString must not be provided for this vaccine type"
        )

        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Invalid target_disease
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_target_disease_imms,'test')

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_patient_name_imms,'test')

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Not Applicable field present
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.get_immunization_by_id_all("an-id", bad_na_imms,'test')

        self.assertTrue(bad_na_msg in error.exception.message)
        self.imms_repo.get_immunization_by_id_all.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()
    


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
        self.imms_repo.create_immunization.return_value = create_covid_19_immunization_dict(imms_id)
        pds_patient = {"identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}]}
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict(imms_id, nhs_number)

        # When
        stored_imms = self.fhir_service.create_immunization(req_imms,"COVID19:create", "TestApp")

        # Then
        self.imms_repo.create_immunization.assert_called_once_with(req_imms, pds_patient,"COVID19:create", "TestApp" )
        self.validator.validate.assert_called_once_with(req_imms)
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(nhs_number)
        self.assertIsInstance(stored_imms, Immunization)

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms = create_covid_19_immunization_dict("an-id", "9990548609")
        imms["recorded"] = "20201214"
        expected_msg = 'recorded must be a valid date string in the format "YYYY-MM-DD"'

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(imms,"COVID19:create", "TestApp")

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_post_validation_failed(self):
        """it should throw exception if Immunization is not valid"""

        valid_imms = create_covid_19_immunization_dict("an-id", VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        bad_target_disease_msg = "['bad-code'] is not a valid combination of disease codes for this service"

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"

        bad_na_imms = deepcopy(valid_imms)
        bad_na_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = DiseaseCodes.flu
        bad_na_msg = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='IpAddress')].answer[0].valueString must not be provided for this vaccine type"
        )

        fhir_service = FhirService(self.imms_repo, self.pds_service)

        # Create
        # Invalid target_disease
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_target_disease_imms,"COVID19:create", "TestApp")

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Missing patient name (Mandatory field)
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_patient_name_imms,"COVID19:create", "TestApp")

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

        # Not Applicable field present
        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_na_imms,"COVID19:create", "TestApp")

        self.assertTrue(bad_na_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
        self.pds_service.get_patient_details.assert_not_called()

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_covid_19_immunization_dict("an-id", invalid_nhs_number)

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.create_immunization(bad_patient_imms,"COVID19:create", "TestApp")

        # Then
        self.assertEqual(e.exception.patient_identifier, invalid_nhs_number)
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
        self.imms_repo.update_immunization.return_value = create_covid_19_immunization_dict(imms_id)
        pds_patient = {"identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}]}
        self.fhir_service.pds_service.get_patient_details.return_value = pds_patient

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_19_immunization_dict(imms_id, nhs_number)

        # When
        outcome, _ = self.fhir_service.update_immunization(imms_id, req_imms, 1,"COVID19:update")

        # Then
        self.assertEqual(outcome, UpdateOutcome.UPDATE)
        self.imms_repo.update_immunization.assert_called_once_with(imms_id, req_imms, pds_patient, 1,"COVID19:update")
        self.fhir_service.pds_service.get_patient_details.assert_called_once_with(nhs_number)

    def test_id_not_present(self):
        """it should populate id in the message if it is not present"""
        req_imms_id = "an-id"
        self.imms_repo.update_immunization.return_value = create_covid_19_immunization_dict(req_imms_id)
        self.fhir_service.pds_service.get_patient_details.return_value = {
            "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9990548609"}]
        }

        req_imms = create_covid_19_immunization_dict("we-will-remove-this-id")
        del req_imms["id"]

        # When
        self.fhir_service.update_immunization(req_imms_id, req_imms, 1,"COVID19:update")

        # Then
        passed_imms = self.imms_repo.update_immunization.call_args.args[1]
        self.assertEqual(passed_imms["id"], req_imms_id)

    def test_patient_error(self):
        """it should throw error when PDS can't resolve patient"""
        self.fhir_service.pds_service.get_patient_details.return_value = None
        imms_id = "an-id"
        invalid_nhs_number = "a-bad-patient-id"
        bad_patient_imms = create_covid_19_immunization_dict(imms_id, invalid_nhs_number)

        with self.assertRaises(InvalidPatientId) as e:
            # When
            self.fhir_service.update_immunization(imms_id, bad_patient_imms, 1,"COVID19:update")

        # Then
        self.assertEqual(e.exception.patient_identifier, invalid_nhs_number)
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
        imms = json.loads(create_covid_19_immunization(imms_id).json())
        self.imms_repo.delete_immunization.return_value = imms

        # When
        act_imms = self.fhir_service.delete_immunization(imms_id, "COVID:delete")

        # Then
        self.imms_repo.delete_immunization.assert_called_once_with(imms_id, "COVID:delete")
        self.assertIsInstance(act_imms, Immunization)
        self.assertEqual(act_imms.id, imms_id)


class TestSearchImmunizations(unittest.TestCase):
    """Tests for FhirService.search_immunizations"""

    def setUp(self):
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.pds_service = create_autospec(PdsService)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.pds_service, self.validator)
        self.nhs_search_param = "patient.identifier"
        self.vaccine_type_search_param = "-immunization.target"

    def test_vaccine_type_search(self):
        """It should search for the correct vaccine type"""
        nhs_number = VALID_NHS_NUMBER
        vaccine_type = VaccineTypes.covid_19
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_type}"

        # When
        _ = self.fhir_service.search_immunizations(nhs_number, [vaccine_type], params)

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(nhs_number, [vaccine_type])

    def test_make_fhir_bundle_from_search_result(self):
        """It should return a FHIR Bundle resource"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_types}"
        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, params)
        # Then
        self.assertIsInstance(result, FhirBundle)
        self.assertEqual(result.type, "searchset")
        self.assertEqual(len(imms_ids), len(result.entry))
        # Assert each entry in the bundle
        for i, entry in enumerate(result.entry):
            self.assertIsInstance(entry, BundleEntry)
            self.assertEqual(entry.resource.resource_type, "Immunization")
            self.assertEqual(entry.resource.id, imms_ids[i])
        # Assert self link
        self.assertEqual(len(result.link), 1)
        self.assertEqual(result.link[0].relation, "self")

    def test_date_from_is_used_to_filter(self):
        """It should return only Immunizations after date_from"""
        imms = [("imms-1", "2021-02-07T13:28:17.271+00:00"), ("imms-2", "2021-02-08T13:28:17.271+00:00")]
        imms_list = [
            create_covid_19_immunization_dict(imms_id, occurrence_date_time=occcurrence_date_time)
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        # Day before.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 6)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # When
        # Day of first, inclusive search.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 7)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # When
        # Day of second, inclusive search.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 8)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(1, len(searched_imms))
        self.assertEqual(imms_ids[1], searched_imms[0].resource.id)

        # When
        # Day after.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 2, 9)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(0, len(searched_imms))

    def test_date_from_is_optional(self):
        """It should return everything when no date_from is specified"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_from=datetime.date(2021, 3, 6)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_date_to_is_used_to_filter(self):
        """It should return only Immunizations before date_to"""
        imms = [("imms-1", "2021-02-07T13:28:17.271+00:00"), ("imms-2", "2021-02-08T13:28:17.271+00:00")]
        imms_list = [
            create_covid_19_immunization_dict(imms_id, occurrence_date_time=occcurrence_date_time)
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        # Day after.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 9)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # When
        # Day of second, inclusive search.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 8)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # When
        # Day of first, inclusive search.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 7)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 1)
        self.assertEqual(searched_imms[0].resource.id, imms_ids[0])

        # When
        # Day before.
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 2, 6)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 0)

    def test_date_to_is_optional(self):
        """It should return everything when no date_to is specified"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # When
        result = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, "", date_to=datetime.date(2021, 3, 8)
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_matches_contain_fullUrl(self):
        """All matches must have a fullUrl consisting of their id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")
        entries = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(entries):
            self.assertEqual(entry.fullUrl, f"urn:uuid:{imms_ids[i]}")

    @unittest.skip("Patient fullUrl not implemented")
    def test_patient_contains_fullUrl(self):
        """Patient must have a fullUrl consisting of its id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = {}
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next((entry for entry in result.entry if entry.resource.resource_type == "Patient"), None)
        self.assertEqual(patient_entry.fullUrl, "???")

    def test_patient_included(self):
        """Patient is included in the results."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        patient = next(contained for contained in imms_list[0]["contained"] if contained["resourceType"] == "Patient")
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = patient
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next((entry for entry in result.entry if entry.resource.resource_type == "Patient"), None)
        self.assertIsNotNone(patient_entry)

    def test_patient_is_stripped(self):
        """The included Patient is a subset of the data."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_19_immunization_dict(imms_id) for imms_id in imms_ids]
        patient = next(contained for contained in imms_list[0]["contained"] if contained["resourceType"] == "Patient")
        self.imms_repo.find_immunizations.return_value = imms_list
        self.pds_service.get_patient_details.return_value = patient
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = [VaccineTypes.covid_19]

        # When
        result = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "")

        # Then
        patient_entry = next((entry for entry in result.entry if entry.resource.resource_type == "Patient"))
        patient_entry_resource = patient_entry.resource
        fields_to_keep = ["id", "resource_type", "identifier", "birthDate"]
        # self.assertListEqual(sorted(vars(patient_entry.resource).keys()), sorted(fields_to_keep))
        # self.assertGreater(len(patient), len(fields_to_keep))
        for field in fields_to_keep:
            self.assertTrue(hasattr(patient_entry_resource, field), f"{field} in Patient")
            self.assertIsNotNone(getattr(patient_entry_resource, field))

        for k, v in vars(patient_entry_resource).items():
            if k not in fields_to_keep:
                self.assertIsNone(v)