import os


def get_env_var(var_name: str) -> str:
    value = os.getenv(var_name)

    if not value:
        raise EnvironmentError(f"{var_name} environment variable is required")

    return value


def get_apigee_username() -> str:
    return get_env_var("APIGEE_USERNAME")


def get_proxy_name() -> str:
    return get_env_var("PROXY_NAME")


def is_pr_env() -> bool:
    """Checks if the tests are running against a dynamic PR environment"""
    proxy_name = get_proxy_name()
    return proxy_name.startswith("immunisation-fhir-api-pr-")


def get_apigee_access_token() -> str:
    return get_env_var("APIGEE_ACCESS_TOKEN")
