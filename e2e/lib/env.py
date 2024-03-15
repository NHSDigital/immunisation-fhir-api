import logging
import os
import subprocess

from .apigee import ApigeeEnv
from .authentication import AppRestrictedCredentials

"""use functions in this module to get configs that can be read from environment variables or external processes"""


def get_apigee_username():
    if username := os.getenv("APIGEE_USERNAME"):
        return username
    else:
        logging.error('environment variable "APIGEE_USERNAME" is required')


def get_apigee_env() -> ApigeeEnv:
    if env := os.getenv("APIGEE_ENVIRONMENT"):
        try:
            return ApigeeEnv(env)
        except ValueError:
            logging.error(f'the environment variable "APIGEE_ENVIRONMENT: {env}" is invalid')
    else:
        logging.warning('the environment variable "APIGEE_ENVIRONMENT" is empty, '
                        'falling back to the default value: "internal-dev"')
        return ApigeeEnv.INTERNAL_DEV


def get_apigee_access_token(username: str = None):
    if access_token := os.getenv("APIGEE_ACCESS_TOKEN"):
        return access_token

    if username := username or get_apigee_username():
        env = os.environ.copy()
        env["SSO_LOGIN_URL"] = env.get("SSO_LOGIN_URL", "https://login.apigee.com")
        try:
            res = subprocess.run(["get_token", "-u", username], env=env, stdout=subprocess.PIPE, text=True)
            return res.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError("Make sure you install apigee's get_token utility and make sure it's in your PATH. "
                               "Follow: https://docs.apigee.com/api-platform/system-administration/using-gettoken")


def get_default_app_restricted_credentials() -> AppRestrictedCredentials:
    client_id = os.getenv("DEFAULT_CLIENT_ID")
    kid = os.getenv("DEFAULT_APP_ID")
    if not client_id or not kid:
        raise RuntimeError('Both "DEFAULT_CLIENT_ID" and "DEFAULT_APP_ID" are required')
    private_key = get_private_key()

    return AppRestrictedCredentials(client_id=client_id, kid=kid, private_key_content=private_key)


def get_private_key_path() -> str:
    if not os.getenv("APP_RESTRICTED_PRIVATE_KEY_PATH"):
        raise RuntimeError('"APP_RESTRICTED_PRIVATE_KEY_PATH" is required')
    return os.getenv("APP_RESTRICTED_PRIVATE_KEY_PATH")


def get_public_key_path() -> str:
    if not os.getenv("APP_RESTRICTED_PUBLIC_KEY_PATH"):
        raise RuntimeError('"APP_RESTRICTED_PUBLIC_KEY_PATH" is required')
    return os.getenv("APP_RESTRICTED_PUBLIC_KEY_PATH")


def get_private_key(file_path: str = None) -> str:
    file_path = file_path if file_path else get_private_key_path()
    with open(file_path, "r") as f:
        return f.read()


def get_auth_url(apigee_env: ApigeeEnv = None) -> str:
    if not apigee_env:
        apigee_env = get_apigee_env()

    if apigee_env == ApigeeEnv.PROD:
        return "https://api.service.nhs.uk/oauth2"
    else:
        return f"https://{apigee_env.value}.api.service.nhs.uk/oauth2-mock"


def get_proxy_name() -> str:
    if not os.getenv("PROXY_NAME"):
        raise RuntimeError('"PROXY_NAME" is required')
    return os.getenv("PROXY_NAME")


def get_service_base_path(apigee_env: ApigeeEnv = None) -> str:
    if not os.getenv("SERVICE_BASE_PATH"):
        raise RuntimeError('"SERVICE_BASE_PATH" is required')
    apigee_env = apigee_env if apigee_env else get_apigee_env()

    base_path = os.getenv("SERVICE_BASE_PATH")
    return f"https://{apigee_env.value}.api.service.nhs.uk/{base_path}"


def get_status_endpoint_api_key() -> str:
    if not os.getenv("STATUS_API_KEY"):
        raise RuntimeError('"STATUS_API_KEY" is required')
    return os.getenv("STATUS_API_KEY")


def get_source_commit_id() -> str:
    return os.getenv("SOURCE_COMMIT_ID")
