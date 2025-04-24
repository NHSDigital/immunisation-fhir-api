import base64
import json
import jwt
import requests
import time
import uuid
from enum import Enum

from cache import Cache
from models.errors import UnhandledResponseError


class Service(Enum):
    PDS = "pds"
    IMMUNIZATION = "imms"


class AppRestrictedAuth:
    def __init__(
        self, service: Service, secret_manager_client, environment, cache: Cache
    ):
        self.secret_manager_client = secret_manager_client
        self.cache = cache
        self.cache_key = f"{service.value}_access_token"

        self.expiry = 30
        self.secret_name = (
            f"imms/pds/{environment}/jwt-secrets"
            if service == Service.PDS
            else f"imms/immunization/{environment}/jwt-secrets"
        )

        self.token_url = (
            f"https://{environment}.api.service.nhs.uk/oauth2/token"
            if environment != "prod"
            else "https://api.service.nhs.uk/oauth2/token"
        )

    def get_service_secrets(self):
        kwargs = {"SecretId": self.secret_name}
        response = self.secret_manager_client.get_secret_value(**kwargs)
        secret_object = json.loads(response["SecretString"])
        secret_object["private_key"] = base64.b64decode(
            secret_object["private_key_b64"]
        ).decode()

        return secret_object

    def create_jwt(self, now: int):
        secret_object = self.get_service_secrets()
        claims = {
            "iss": secret_object["api_key"],
            "sub": secret_object["api_key"],
            "aud": self.token_url,
            "iat": now,
            "exp": now + self.expiry,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(
            claims,
            secret_object["private_key"],
            algorithm="RS512",
            headers={"kid": secret_object["kid"]},
        )

    def get_access_token(self):
        now = int(time.time())
        cached = self.cache.get(self.cache_key)
        if cached and cached["expires_at"] > now:
            return cached["token"]

        _jwt = self.create_jwt(now)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": _jwt,
        }
        token_response = requests.post(self.token_url, data=data, headers=headers)
        if token_response.status_code != 200:
            raise UnhandledResponseError(
                response=token_response.text, message="Failed to get access token"
            )

        token = token_response.json().get("access_token")

        self.cache.put(
            self.cache_key, {"token": token, "expires_at": now + self.expiry}
        )

        return token
