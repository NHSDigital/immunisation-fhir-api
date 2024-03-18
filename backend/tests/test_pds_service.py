import base64
import json
import time
import unittest
from unittest.mock import create_autospec, MagicMock, patch, ANY

import responses
from models.errors import UnhandledResponseError
from pds_service import PdsService, Authenticator
from responses import matchers


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


class TestAuthenticator(unittest.TestCase):
    def setUp(self):
        self.kid = "a_kid"
        self.api_key = "an_api_key"
        self.private_key = "a_private_key"
        # The private key must be stored as base64 encoded in secret-manager
        b64_private_key = base64.b64encode(self.private_key.encode()).decode()

        pds_secret = {"private_key_b64": b64_private_key, "kid": self.kid, "api_key": self.api_key}
        secret_response = {"SecretString": json.dumps(pds_secret)}

        self.secret_manager_client = MagicMock()
        self.secret_manager_client.get_secret_value.return_value = secret_response

        self.cache = MagicMock()
        self.cache.get.return_value = None

        env = "an-env"
        self.authenticator = Authenticator(self.secret_manager_client, env, self.cache)
        self.url = f"https://{env}.api.service.nhs.uk/oauth2/token"

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

    def test_env_mapping(self):
        """it should target int environment for none-prod environment, otherwise int"""
        # For env=none-prod
        env = "some-env"
        auth = Authenticator(None, env, None)
        self.assertTrue(auth.token_url.startswith(f"https://{env}."))

        # For env=prod
        env = "prod"
        auth = Authenticator(None, env, None)
        self.assertTrue(env not in auth.token_url)

    def test_returned_cached_token(self):
        """it should return cached token"""
        cached_token = {
            "token": "a-cached-access-token",
            "expires_at": int(time.time()) + 99999  # make sure it's not expired
        }
        self.cache.get.return_value = cached_token

        # When
        token = self.authenticator.get_access_token()

        # Then
        self.assertEqual(token, cached_token["token"])
        self.secret_manager_client.assert_not_called()

    @responses.activate
    def test_update_cache(self):
        """it should update cached token"""
        self.cache.get.return_value = None
        token = "a-new-access-token"
        cached_token = {
            "token": token,
            "expires_at": ANY
        }
        responses.add(responses.POST, self.url, status=200, json={"access_token": token})

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = "a-jwt"
            # When
            self.authenticator.get_access_token()

        # Then
        self.cache.put.assert_called_once_with("pds_access_token", cached_token)

    @responses.activate
    def test_expired_token_in_cache(self):
        """it should not return cached access token if it's expired"""
        now_epoch = 12345
        expires_at = now_epoch + self.authenticator.expiry
        cached_token = {
            "token": "an-expired-cached-access-token",
            "expires_at": expires_at,
        }
        self.cache.get.return_value = cached_token

        new_token = "a-new-token"
        responses.add(responses.POST, self.url, status=200, json={"access_token": new_token})

        new_now = expires_at  # this is to trigger expiry and also the mocked now-time when storing the new token
        with patch("jwt.encode") as mock_jwt:
            with patch("time.time") as mock_time:
                mock_time.return_value = new_now
                mock_jwt.return_value = "a-jwt"
                # When
                self.authenticator.get_access_token()

        # Then
        exp_cached_token = {
            "token": new_token,
            "expires_at": new_now + self.authenticator.expiry
        }
        self.cache.put.assert_called_once_with(ANY, exp_cached_token)

    @responses.activate
    def test_uses_cache_for_token(self):
        """it should use the cache for the PDS auth call"""

        token = "a-new-access-token"
        token_call = responses.add(responses.POST, self.url, status=200, json={"access_token": token})
        values = {}

        def get_side_effect(key):
            return values.get(key, None)

        def put_side_effect(key, value):
            values[key] = value

        self.cache.get.side_effect = get_side_effect
        self.cache.put.side_effect = put_side_effect

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = "a-jwt"
            # When
            self.assertEqual(0, token_call.call_count)
            self.authenticator.get_access_token()
            self.assertEqual(1, token_call.call_count)
            self.authenticator.get_access_token()
            self.assertEqual(1, token_call.call_count)
