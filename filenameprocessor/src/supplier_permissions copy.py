"""Functions for fetching supplier permissions"""

from clients import logger, redis_client
import json
from errors import VaccineTypePermissionsError


def get_supplier_permissions(supplier: str) -> list[str]:
    """
    Returns the permissions for the given supplier.
    Defaults return value is an empty list, including when the supplier has no permissions.
    """
     
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    if not permissions_data:
        return []
    return json.loads(permissions_data)

def validate_vaccine_type_permissions(vaccine_type: str, supplier: str) -> list:
    """
    Returns the list of permissions for the given supplier.
    Raises an exception if the supplier does not have at least one permission for the vaccine type.
    """
    supplier_permissions = get_supplier_permissions(supplier)

    # Validate that supplier has at least one permissions for the vaccine type
    if not any(permission.split(".")[0] == vaccine_type for permission in supplier_permissions):
        error_message = f"Initial file validation failed: {supplier} does not have permissions for {vaccine_type}"
        logger.error(error_message)
        raise VaccineTypePermissionsError(error_message)

    return supplier_permissions
