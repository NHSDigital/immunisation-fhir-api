import responses
import unittest
from responses import matchers
from unittest.mock import create_autospec

from authentication import AppRestrictedAuth
from models.errors import UnhandledResponseError
from pds_service import PdsService

"test"


class TestPdsService(unittest.TestCase):
    def setUp(self):
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.access_token = "an-access-token"
        self.authenticator.get_access_token.return_value = self.access_token

        env = "an-env"
        self.base_url = (
            f"https://{env}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
        )
        self.pds_service = PdsService(self.authenticator, env)

    @responses.activate
    def test_get_patient_details(self):
        """it should send a GET request to PDS"""
        patient_id = "900000009"
        act_res = {"id": patient_id}
        exp_header = {"Authorization": f"Bearer {self.access_token}"}
        pds_url = f"{self.base_url}/{patient_id}"
        responses.add(
            responses.GET,
            pds_url,
            json=act_res,
            status=200,
            match=[matchers.header_matcher(exp_header)],
        )

        # When
        patient = self.pds_service.get_patient_details(patient_id)

        # Then
        self.assertDictEqual(patient, act_res)

    @responses.activate
    def test_get_patient_details_not_found(self):
        """it should return None if patient doesn't exist or if there is any error"""
        patient_id = "900000009"
        responses.add(responses.GET, f"{self.base_url}/{patient_id}", status=404)

        # When
        patient = self.pds_service.get_patient_details(patient_id)

        # Then
        self.assertIsNone(patient)

    @responses.activate
    def test_get_patient_details_error(self):
        """it should raise exception if PDS responded with error"""
        patient_id = "900000009"
        response = {"msg": "an-error"}
        responses.add(
            responses.GET, f"{self.base_url}/{patient_id}", status=400, json=response
        )

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.pds_service.get_patient_details(patient_id)

        # Then
        self.assertDictEqual(e.exception.response, response)

    def test_env_mapping(self):
        """it should target int environment for none-prod environment, otherwise int"""
        # For env=none-prod
        env = "some-env"
        service = PdsService(None, env)
        self.assertTrue(service.base_url.startswith(f"https://{env}."))

        # For env=prod
        env = "prod"
        service = PdsService(None, env)
        self.assertTrue(env not in service.base_url)
