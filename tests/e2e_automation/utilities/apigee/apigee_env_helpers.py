import os

PROXY_PR_PREFIX = "immunisation-fhir-api-pr-"
SANDBOX_PROXY_NAME = "immunisation-fhir-api-sandbox"
INT_PROXY_NAME = "immunisation-fhir-api-int"


def get_env_var(var_name: str) -> str:
    value = os.getenv(var_name)

    if not value:
        raise EnvironmentError(f"{var_name} environment variable is required")

    return value


def get_apigee_username() -> str:
    return get_env_var("APIGEE_USERNAME")


def get_proxy_name() -> str:
    return get_env_var("PROXY_NAME")


def use_temp_apigee_apps() -> bool:
    """
    Determines if temporary Apigee Apps are required for the test run based on the following business logic:
    - dynamic PR environments always require temporary apps
    - Apigee non-prod environments (everything except sandbox, int and prod) use dynamic apps unless the user provides
    the USE_STATIC_APPS env var to override this
    """
    if is_pr_env():
        return True

    proxy_name = get_proxy_name()

    if proxy_name == INT_PROXY_NAME or proxy_name == SANDBOX_PROXY_NAME:
        return False

    return os.getenv("USE_STATIC_APPS", "False") != "True"


def is_pr_env() -> bool:
    """Checks if the tests are running against a dynamic PR environment"""
    proxy_name = get_proxy_name()
    return proxy_name.startswith(PROXY_PR_PREFIX)


def get_apigee_access_token() -> str:
    return get_env_var("APIGEE_ACCESS_TOKEN")


def get_apigee_environment() -> str:
    return get_env_var("APIGEE_ENVIRONMENT")
