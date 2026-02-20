from typing import Optional

from common.constants import DEFAULT_BASE_PATH, PR_ENV_PREFIX


def get_service_url(service_env: Optional[str], service_base_path: Optional[str]) -> str:
    """Sets the service URL based on service parameters derived from env vars. PR environments use internal-dev while
    we also default to this environment. The only other exceptions are preprod which maps to the Apigee int environment
    and prod which does not have a subdomain."""
    if not service_base_path:
        service_base_path = DEFAULT_BASE_PATH

    if service_env is None or is_pr_env(service_env):
        subdomain = "internal-dev."
    elif service_env == "preprod":
        subdomain = "int."
    elif service_env == "prod":
        subdomain = ""
    else:
        subdomain = f"{service_env}."

    return f"https://{subdomain}api.service.nhs.uk/{service_base_path}"


def is_pr_env(service_env: Optional[str]) -> bool:
    return service_env is not None and service_env.startswith(PR_ENV_PREFIX)
