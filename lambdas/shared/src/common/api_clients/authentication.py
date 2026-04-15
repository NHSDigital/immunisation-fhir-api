import base64
import json
import time
import uuid
from typing import Any

import jwt
import requests

from common.api_clients.constants import (
    ACCESS_TOKEN_EXPIRY_SECONDS,
    ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS,
    CLIENT_ASSERTION_TYPE_JWT_BEARER,
    CONTENT_TYPE_X_WWW_FORM_URLENCODED,
    GRANT_TYPE_CLIENT_CREDENTIALS,
    JWT_EXPIRY_SECONDS,
)
from common.clients import logger
from common.models.errors import UnhandledResponseError


class AppRestrictedAuth:
    def __init__(self, secret_manager_client: Any, environment: str, secret_name: str | None = None):
        self.secret_manager_client = secret_manager_client

        self.cached_access_token: str | None = None
        self.cached_access_token_expiry_time: int | None = None
        self.cached_service_secrets: dict[str, Any] | None = None

        self.secret_name = f"imms/outbound/{environment}/jwt-secrets" if secret_name is None else secret_name
        self.token_url = (
            f"https://{environment}.api.service.nhs.uk/oauth2/token"
            if environment != "prod"
            else "https://api.service.nhs.uk/oauth2/token"
        )

    def get_service_secrets(self) -> dict[str, Any]:
        if self.cached_service_secrets is not None:
            return self.cached_service_secrets

        response = self.secret_manager_client.get_secret_value(SecretId=self.secret_name)
        secret_object = json.loads(response["SecretString"])
        secret_object["private_key"] = base64.b64decode(secret_object["private_key_b64"]).decode()

        self.cached_service_secrets = secret_object
        return secret_object

    def create_jwt(self, now: int) -> str:
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

    def _request_access_token(self, jwt_assertion: str) -> requests.Response:
        return requests.post(
            self.token_url,
            data={
                "grant_type": GRANT_TYPE_CLIENT_CREDENTIALS,
                "client_assertion_type": CLIENT_ASSERTION_TYPE_JWT_BEARER,
                "client_assertion": jwt_assertion,
            },
            headers={"Content-Type": CONTENT_TYPE_X_WWW_FORM_URLENCODED},
            timeout=10,
        )

    def get_access_token(self) -> str:
        now = int(time.time())

        if (
            self.cached_access_token
            and self.cached_access_token_expiry_time is not None
            and self.cached_access_token_expiry_time > now + ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS
        ):
            return self.cached_access_token

        logger.info("Requesting new access token")
        jwt_assertion = self.create_jwt(now)

        try:
            token_response = self._request_access_token(jwt_assertion)
        except requests.RequestException as error:
            logger.exception("Failed to fetch access token from %s", self.token_url)
            raise UnhandledResponseError(response=str(error), message="Failed to get access token") from error

        if token_response.status_code != 200:
            raise UnhandledResponseError(response=token_response.text, message="Failed to get access token")

        token = token_response.json().get("access_token")
        self.cached_access_token = token
        self.cached_access_token_expiry_time = now + ACCESS_TOKEN_EXPIRY_SECONDS
        return token
