import responses
import unittest
from responses import matchers
from unittest.mock import create_autospec, ANY, patch

from authentication import AppRestrictedAuth
from batch.errors import ImmunizationApiError, ImmunizationApiUnhandledError
from batch.immunization_api import ImmunizationApi


class TestImmunizationApi(unittest.TestCase):
    def setUp(self):
        self.authenticator = create_autospec(AppRestrictedAuth)
        self.api = ImmunizationApi(
            authenticator=self.authenticator,
            environment="a_env"
        )

    @responses.activate
    def test_create_immunization(self):
        """it should create an immunization"""
        imms_url = self.api.base_url + "/Immunization"
        self.authenticator.get_access_token.return_value = "an-access-token"

        cor_id = "a_cor_id"
        exp_header = {
            'Authorization': f'Bearer an-access-token',
            'X-Request-ID': ANY,
            'X-Correlation-ID': cor_id,
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        exp_response = {"a": "b"}
        responses.add(responses.POST, imms_url, json=exp_response, status=200,
                      match=[matchers.header_matcher(exp_header)])

        # When
        act_response = self.api.create_immunization(exp_response, cor_id)

        # Then
        self.assertDictEqual(act_response.json(), exp_response)

    @responses.activate
    def test_update_immunization(self):
        """it should update an immunization"""
        imms_url = self.api.base_url + "/Immunization"
        # TODO: write it once we know the id

    @responses.activate
    def test_delete_immunization(self):
        """it should delete an immunization"""
        imms_url = self.api.base_url + "/Immunization"
        # TODO: write it once we know the id

    @responses.activate
    def test_non_200_error(self):
        """it should raise an error if response is not 200"""
        imms_url = self.api.base_url + "/Immunization"
        self.authenticator.get_access_token.return_value = "an-access-token"
        responses.add(responses.POST, imms_url, status=400)

        with self.assertRaises(ImmunizationApiError) as e:
            # When
            self.api.create_immunization({}, "")

    def test_unhandled_error(self):
        """it should raise an error if request fails"""
        self.authenticator.get_access_token.return_value = "an-access-token"

        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("an-error")
            with self.assertRaises(ImmunizationApiUnhandledError) as e:
                # When
                self.api.create_immunization({}, "")
