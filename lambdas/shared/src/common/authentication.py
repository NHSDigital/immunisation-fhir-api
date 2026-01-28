import base64
import json
import time
import uuid

import jwt
import requests

from common.clients import logger
from common.models.errors import UnhandledResponseError

GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"
CLIENT_ASSERTION_TYPE_JWT_BEARER = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
CONTENT_TYPE_X_WWW_FORM_URLENCODED = "application/x-www-form-urlencoded"

JWT_EXPIRY_SECONDS = 5 * 60
ACCESS_TOKEN_EXPIRY_SECONDS = 10 * 60
# Throw away the cached token earlier than the exact expiry time so we have enough
# time left to use it (and to account for network latency, clock skew etc.)
ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS = 30


class AppRestrictedAuth:
    def __init__(self, secret_manager_client, environment):
        self.secret_manager_client = secret_manager_client

        self.cached_access_token = None
        self.cached_access_token_expiry_time = None

        self.secret_name = f"imms/pds/{environment}/jwt-secrets"

        self.token_url = (
            f"https://{environment}.api.service.nhs.uk/oauth2/token"
            if environment != "prod"
            else "https://api.service.nhs.uk/oauth2/token"
        )

    def get_service_secrets(self):
        response = self.secret_manager_client.get_secret_value(SecretId=self.secret_name)
        secret_object = json.loads(response["SecretString"])
        secret_object["private_key"] = base64.b64decode(secret_object["private_key_b64"]).decode()
        return secret_object

    def create_jwt(self, now: int):
        secret_object = self.get_service_secrets()
        return jwt.encode(
            {
                "iss": secret_object["api_key"],
                "sub": secret_object["api_key"],
                "aud": self.token_url,
                "iat": now,
                "exp": now + JWT_EXPIRY_SECONDS,
                "jti": str(uuid.uuid4()),
            },
            secret_object["private_key"],
            algorithm="RS512",
            headers={"kid": secret_object["kid"]},
        )

    def get_access_token(self):
        now = int(time.time())

        if (
            self.cached_access_token
            and self.cached_access_token_expiry_time > now + ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS
        ):
            return self.cached_access_token

        logger.info("Requesting new access token")
        jwt = self.create_jwt(now)

        token_response = requests.post(
            self.token_url,
            data={
                "grant_type": GRANT_TYPE_CLIENT_CREDENTIALS,
                "client_assertion_type": CLIENT_ASSERTION_TYPE_JWT_BEARER,
                "client_assertion": jwt,
            },
            headers={"Content-Type": CONTENT_TYPE_X_WWW_FORM_URLENCODED},
        )
        if token_response.status_code != 200:
            raise UnhandledResponseError(response=token_response.text, message="Failed to get access token")

        token = token_response.json().get("access_token")
        self.cached_access_token = token
        self.cached_access_token_expiry_time = now + ACCESS_TOKEN_EXPIRY_SECONDS
        return token
