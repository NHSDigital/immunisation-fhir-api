import base64
import json
import jwt
import requests
import time
import uuid
from enum import Enum

from .cache import Cache
from common.models.errors import UnhandledResponseError
from common.clients import logger


class Service(Enum):
    PDS = "pds"
    IMMUNIZATION = "imms"


class AppRestrictedAuth:
    def __init__(self, service: Service, secret_manager_client, environment, cache: Cache):
        self.secret_manager_client = secret_manager_client
        self.cache = cache
        self.cache_key = f"{service.value}_access_token"

        self.expiry = 30
        self.secret_name = f"imms/pds/{environment}/jwt-secrets" if service == Service.PDS else \
            f"imms/immunization/{environment}/jwt-secrets"

        self.token_url = f"https://{environment}.api.service.nhs.uk/oauth2/token" \
            if environment != "prod" else "https://api.service.nhs.uk/oauth2/token"

    def get_service_secrets(self):
        kwargs = {"SecretId": self.secret_name}
        response = self.secret_manager_client.get_secret_value(**kwargs)
        secret_object = json.loads(response['SecretString'])
        secret_object['private_key'] = base64.b64decode(secret_object['private_key_b64']).decode()

        return secret_object

    def create_jwt(self, now: int):
        logger.info("create_jwt")
        secret_object = self.get_service_secrets()
        logger.info(f"Secret object: {secret_object}")
        claims = {
            "iss": secret_object['api_key'],
            "sub": secret_object['api_key'],
            "aud": self.token_url,
            "iat": now,
            "exp": now + self.expiry,
            "jti": str(uuid.uuid4())
        }
        logger.info(f"JWT claims: {claims}")
        # ✅ Version-compatible JWT encoding
        try:
            # PyJWT 2.x
            return jwt.encode(
                claims,
                secret_object['private_key'],
                algorithm='RS512',
                headers={"kid": secret_object['kid']}
            )
        except TypeError:
            # PyJWT 1.x (older versions return bytes)
            token = jwt.encode(
                claims,
                secret_object['private_key'],
                algorithm='RS512',
                headers={"kid": secret_object['kid']}
            )
            # Convert bytes to string if needed
            return token.decode('utf-8') if isinstance(token, bytes) else token

    def get_access_token(self):
        logger.info("get_access_token")
        now = int(time.time())
        logger.info(f"Current time: {now}, Expiry time: {now + self.expiry}")
        # Check if token is cached and not expired
        logger.info(f"Cache key: {self.cache_key}")
        logger.info("Checking cache for access token")
        cached = self.cache.get(self.cache_key)
        logger.info(f"Cached token: {cached}")
        if cached and cached["expires_at"] > now:
            logger.info("Returning cached access token")
            return cached["token"]

        logger.info("No valid cached token found, creating new token")
        _jwt = self.create_jwt(now)

        logger.info(f"JWT created: {_jwt}")

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': _jwt
        }
        token_response = requests.post(self.token_url, data=data, headers=headers)
        if token_response.status_code != 200:
            raise UnhandledResponseError(response=token_response.text, message="Failed to get access token")

        token = token_response.json().get('access_token')

        self.cache.put(self.cache_key, {"token": token, "expires_at": now + self.expiry})

        return token
