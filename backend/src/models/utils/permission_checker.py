import json
from clients import redis_client
from models.errors import UnauthorizedVaxOnRecordError


class VaccinePermissionChecker:
    """Centralized vaccine permission checker."""

    mapped_operations = {
        "create": "c",
        "read": "r",
        "update": "u",
        "delete": "d",
        "search": "s"
    }

    def __init__(self, supplier_system: str):
        self.supplier_permissions = supplier_system
        self.expanded_permissions = self._expand_permissions(self.supplier_permissions)
    
    # Expand permissions from the supplier's permission list
    @staticmethod    
    def _expand_permissions(supplier_permissions: list[str]) -> set[str]:
        expanded = set()
        for permissions in supplier_permissions:
            if '.' not in permissions:
                continue  # skip invalid format
        vaccine_type, allowed_operations = permissions.split('.', 1)
        vaccine_type = vaccine_type.lower()
        for operation in allowed_operations.lower():
            if operation not in {'c', 'r', 'u', 'd', 's'}:
                raise ValueError(f"Unknown operation code: {operation} in a permission {permissions}")
            expanded.add(f"{vaccine_type}.{operation}")
        return expanded

    # Check if the requested permission is a subset of the expanded permissions
    def _vaccine_permission(self, vaccine_type, operation) -> set:
        
        operation = self.mapped_operations.get(operation.lower())
        if not operation:
            raise ValueError(f"Unsupported operation: {operation}")

        vaccine_permission = set()
        if isinstance(vaccine_type, list):
            for x in vaccine_type:
                vaccine_permission.add(str.lower(f"{x}.{operation}"))
            return vaccine_permission
        else:
            vaccine_permission.add(str.lower(f"{vaccine_type}.{operation}"))
            return vaccine_permission

    # Check if the requested permission is allowed
    def _check_permission(self, requested: set[str]) -> None:
        if not requested.issubset(self.expanded_permissions):
            raise UnauthorizedVaxOnRecordError()
        return None

    # Validate the requested vaccine type and operation against the supplier permissions
    def validate(self, vaccine_type, operation) -> None:
        requested_perm = self._vaccine_permission(vaccine_type, operation)
        self._check_permission(requested_perm)