import base64
import json
import os
import sys
import unittest
from unittest.mock import create_autospec, MagicMock, patch, ANY

import responses
from responses import matchers

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../src")
from pds_service import PdsService
from pds_service import Authenticator
from models.errors import UnhandledResponseError


class TestPdsService(unittest.TestCase):
    def setUp(self):
        self.authenticator = create_autospec(Authenticator)
        self.access_token = "an-access-token"
        self.authenticator.get_access_token.return_value = self.access_token

        env = "an-env"
        self.base_url = f"https://{env}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
        self.pds_service = PdsService(self.authenticator, env)

    @responses.activate
    def test_get_patient_details(self):
        """it should send a GET request to PDS"""
        patient_id = "900000009"
        act_res = {"id": patient_id}
        exp_header = {
            'Authorization': f'Bearer {self.access_token}'
        }
        pds_url = f"{self.base_url}/{patient_id}"
        responses.add(responses.GET, pds_url, json=act_res, status=200,
                      match=[matchers.header_matcher(exp_header)])

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
        responses.add(responses.GET, f"{self.base_url}/{patient_id}", status=400, json=response)

        with self.assertRaises(UnhandledResponseError) as e:
            # When
            self.pds_service.get_patient_details(patient_id)

        # Then
        self.assertDictEqual(e.exception.response, response)


class TestAuthenticator(unittest.TestCase):
    def setUp(self):
        self.secret_manager_client = MagicMock()
        self.kid = "a_kid"
        self.api_key = "an_api_key"
        self.private_key = "a_private_key"
        # The private key must be stored as base64 encoded in secret-manager
        b64_private_key = base64.b64encode(self.private_key.encode()).decode()

        pds_secret = {"private_key": b64_private_key, "kid": self.kid, "api_key": self.api_key}
        secret_response = {"SecretString": json.dumps(pds_secret)}
        self.secret_manager_client.get_secret_value.return_value = secret_response

        # FIXME: AMB-1838 make sure environment is parametrized and tested not hardcoded
        self.authenticator = Authenticator(self.secret_manager_client, "int")
        self.url = "https://int.api.service.nhs.uk/oauth2/token"

    @responses.activate
    def test_post_request_to_token(self):
        """it should send a POST request to oauth2 service"""
        _jwt = "a-jwt"
        request_data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': _jwt
        }
        access_token = "an-access-token"
        responses.add(responses.POST, self.url, status=200, json={"access_token": access_token},
                      match=[matchers.urlencoded_params_matcher(request_data)])

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = _jwt
            # When
            act_access_token = self.authenticator.get_access_token()

            # Then
            self.assertEqual(act_access_token, access_token)

    @responses.activate
    def test_jwt_values(self):
        """it should send correct claims and header"""
        claims = {
            "iss": self.api_key,
            "sub": self.api_key,
            "aud": self.url,
            "iat": ANY,
            "exp": ANY,
            "jti": ANY
        }
        _jwt = "a-jwt"
        access_token = "an-access-token"

        responses.add(responses.POST, self.url, status=200, json={"access_token": access_token})

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = _jwt
            # When
            self.authenticator.get_access_token()
            # Then
            mock_jwt.assert_called_once_with(claims, self.private_key,
                                             algorithm="RS512", headers={"kid": self.kid})