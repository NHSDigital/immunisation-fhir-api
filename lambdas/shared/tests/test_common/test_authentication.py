import base64
import json
import time
import unittest
from unittest.mock import ANY, MagicMock, patch

import responses
from responses import matchers

from common.authentication import ACCESS_TOKEN_EXPIRY_SECONDS, AppRestrictedAuth
from common.models.errors import UnhandledResponseError


class TestAuthenticator(unittest.TestCase):
    def setUp(self):
        self.kid = "a_kid"
        self.api_key = "an_api_key"
        self.private_key = "a_private_key"
        # The private key must be stored as base64 encoded in secret-manager
        b64_private_key = base64.b64encode(self.private_key.encode()).decode()

        pds_secret = {
            "private_key_b64": b64_private_key,
            "kid": self.kid,
            "api_key": self.api_key,
        }
        secret_response = {"SecretString": json.dumps(pds_secret)}

        self.secret_manager_client = MagicMock()
        self.secret_manager_client.get_secret_value.return_value = secret_response

        env = "an-env"
        self.authenticator = AppRestrictedAuth(self.secret_manager_client, env)
        self.url = f"https://{env}.api.service.nhs.uk/oauth2/token"

    @responses.activate
    def test_post_request_to_token(self):
        """it should send a POST request to oauth2 service"""
        _jwt = "a-jwt"
        request_data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": _jwt,
        }
        access_token = "an-access-token"
        responses.add(
            responses.POST,
            self.url,
            status=200,
            json={"access_token": access_token},
            match=[matchers.urlencoded_params_matcher(request_data)],
        )

        with patch("common.authentication.jwt.encode") as mock_jwt:
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
            "jti": ANY,
        }
        _jwt = "a-jwt"
        access_token = "an-access-token"

        responses.add(responses.POST, self.url, status=200, json={"access_token": access_token})

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = _jwt
            # When
            self.authenticator.get_access_token()
            # Then
            mock_jwt.assert_called_once_with(claims, self.private_key, algorithm="RS512", headers={"kid": self.kid})

    def test_env_mapping(self):
        """it should target int environment for none-prod environment, otherwise int"""
        # For env=none-prod
        env = "some-env"
        auth = AppRestrictedAuth(None, env)
        self.assertTrue(auth.token_url.startswith(f"https://{env}."))

        # For env=prod
        env = "prod"
        auth = AppRestrictedAuth(None, env)
        self.assertNotIn(env, auth.token_url)

    def test_returned_cached_token(self):
        """it should return cached token"""
        self.authenticator.cached_access_token = "a-cached-access-token"
        self.authenticator.cached_access_token_expiry_time = int(time.time()) + 99999  # make sure it's not expired

        # When
        token = self.authenticator.get_access_token()

        # Then
        self.assertEqual(token, "a-cached-access-token")
        self.secret_manager_client.assert_not_called()

    @responses.activate
    def test_update_cache(self):
        """it should update cached token"""
        token = "a-new-access-token"
        responses.add(responses.POST, self.url, status=200, json={"access_token": token})

        with patch("jwt.encode") as mock_jwt:
            mock_jwt.return_value = "a-jwt"
            # When
            self.authenticator.get_access_token()

        # Then
        self.assertEqual(self.authenticator.cached_access_token, "a-new-access-token")

    @responses.activate
    def test_expired_token_in_cache(self):
        """it should not return cached access token if it's expired"""
        now_epoch = 12345
        expires_at = now_epoch + ACCESS_TOKEN_EXPIRY_SECONDS
        self.authenticator.cached_access_token = ("an-expired-cached-access-token",)
        self.authenticator.cached_access_token_expiry_time = expires_at

        new_token = "a-new-token"
        responses.add(responses.POST, self.url, status=200, json={"access_token": new_token})

        new_now = expires_at  # this is to trigger expiry and also the mocked now-time when storing the new token
        with patch("common.authentication.jwt.encode") as mock_jwt:
            with patch("time.time") as mock_time:
                mock_time.return_value = new_now
                mock_jwt.return_value = "a-jwt"
                # When
                self.authenticator.get_access_token()

        # Then
        self.assertEqual(self.authenticator.cached_access_token, new_token)
        self.assertEqual(self.authenticator.cached_access_token_expiry_time, new_now + ACCESS_TOKEN_EXPIRY_SECONDS)

    @responses.activate
    def test_raise_exception(self):
        """it should raise exception if auth response is not 200"""
        responses.add(responses.POST, self.url, status=400)

        with patch("common.authentication.jwt.encode") as mock_jwt:
            mock_jwt.return_value = "a-jwt"
            with self.assertRaises(UnhandledResponseError):
                # When
                self.authenticator.get_access_token()
