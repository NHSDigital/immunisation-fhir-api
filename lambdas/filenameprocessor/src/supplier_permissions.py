"""Functions for fetching supplier permissions"""

from common.clients import logger
from constants import Operation
from elasticache import get_supplier_permissions_from_cache, get_supplier_system_from_cache
from models.errors import VaccineTypePermissionsError


def validate_vaccine_type_permissions(vaccine_type: str, supplier: str) -> list:
    """
    Returns the list of permissions for the given supplier.
    Raises an exception if the supplier does not have at least one permission for the vaccine type.
    """
    supplier_permissions = get_supplier_permissions_from_cache(supplier)

    # Validate that supplier has at least one permissions for the vaccine type
    if not any(permission.split(".")[0] == vaccine_type for permission in supplier_permissions):
        error_message = f"Initial file validation failed: {supplier} does not have permissions for {vaccine_type}"
        logger.error(error_message)
        raise VaccineTypePermissionsError(error_message)

    return supplier_permissions


def validate_permissions_for_extended_attributes_files(vaccine_type: str, ods_code: str) -> str:
    """
    Checks that the supplier has COVID vaccine type and its CUD permissions.
    Raises an exception if the supplier does not have at least one permission for the vaccine type.
    """
    allowed_operations = {
        Operation.CREATE,
        Operation.UPDATE,
        Operation.DELETE,
    }
    supplier = get_supplier_system_from_cache(ods_code)
    supplier_permissions = get_supplier_permissions_from_cache(supplier)
    cached_operations = [
        permission.split(".")[1] for permission in supplier_permissions if permission.split(".")[0] == vaccine_type
    ]
    if not (cached_operations and allowed_operations.issubset(set(cached_operations[0]))):
        error_message = f"Initial file validation failed: {supplier} does not have permissions for {vaccine_type}"
        logger.error(error_message)
        raise VaccineTypePermissionsError(error_message)

    return f"{ods_code}_{vaccine_type}"
