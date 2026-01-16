import os


# TODO - consolidate methods - just pass the key. Simple!
def get_apigee_username() -> str:
    apigee_username = os.getenv("APIGEE_USERNAME")

    if not apigee_username:
        raise RuntimeError('"APIGEE_USERNAME" environment variable is required')

    return apigee_username


def get_proxy_name() -> str:
    proxy_name = os.getenv("PROXY_NAME")

    if not proxy_name:
        raise RuntimeError('"PROXY_NAME" environment variable is required')

    return proxy_name


def is_pr_env() -> bool:
    """Checks if the tests are running against a dynamic PR environment"""
    proxy_name = get_proxy_name()
    return proxy_name.startswith("immunisation-fhir-api-pr-")


def get_apigee_access_token() -> str:
    access_token = os.getenv("APIGEE_ACCESS_TOKEN")

    if not access_token:
        raise RuntimeError('"PROXY_NAME" environment variable is required')

    return access_token
