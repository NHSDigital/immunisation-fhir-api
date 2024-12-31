"""Functions for fetching supplier permissions"""

import json
from clients import redis_client, logger
from errors import VaccineTypePermissionsError

PERMISSIONS_CONFIG_FILE_KEY = "permissions_config.json"


def get_permissions_config_json_from_cache() -> dict:
    """Gets and returns the permissions config file content from ElastiCache."""
    return json.loads(redis_client.get(PERMISSIONS_CONFIG_FILE_KEY))


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier.
    Defaults return value is an empty list, including when the supplier has no permissions.
    """
    permissions_config = get_permissions_config_json_from_cache()
    return permissions_config.get("all_permissions", {}).get(supplier, [])


def validate_vaccine_type_permissions(vaccine_type: str, supplier: str) -> list:
    """
    Returns the list of permissions for the given supplier.
    Raises an exception if the supplier does not have at least one permission for the vaccine type.
    """
    supplier_permissions = get_supplier_permissions(supplier)

    # Validate that supplier has at least one permissions for the vaccine type
    if not any(vaccine_type in permission for permission in supplier_permissions):
        error_message = f"Initial file validation failed: {supplier} does not have permissions for {vaccine_type}"
        logger.error(error_message)
        raise VaccineTypePermissionsError(error_message)

    return supplier_permissions
