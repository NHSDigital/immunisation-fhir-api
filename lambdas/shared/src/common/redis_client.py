import os

import redis

from common.clients import get_secrets_manager_client, logger

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"
REDIS_AUTH_TOKEN_SECRET_NAME = os.getenv("REDIS_AUTH_TOKEN_SECRET_NAME", "")

redis_client = None
redis_auth_token = None


def get_redis_auth_token():
    global redis_auth_token
    if not REDIS_AUTH_TOKEN_SECRET_NAME:
        return None

    if redis_auth_token is None:
        response = get_secrets_manager_client().get_secret_value(SecretId=REDIS_AUTH_TOKEN_SECRET_NAME)
        redis_auth_token = response["SecretString"]

    return redis_auth_token


def get_redis_client():
    global redis_client
    if redis_client is None:
        logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT} with ssl={REDIS_SSL}")
        redis_client = redis.StrictRedis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=get_redis_auth_token(),
            ssl=REDIS_SSL,
            decode_responses=True,
        )
    return redis_client
