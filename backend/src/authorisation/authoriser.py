import json

from authorisation.api_operation_code import ApiOperationCode
from clients import redis_client, logger
from constants import SUPPLIER_PERMISSIONS_HASH_KEY


class Authoriser:
    def __init__(self):
        self._cache_client = redis_client

    @staticmethod
    def _expand_permissions(permissions: list[str]) -> dict[str, list[ApiOperationCode]]:
        """Parses and expands permissions data into a dictionary mapping vaccination types to a list of permitted
        API operations. The raw string from Redis will be in the form VAC.PERMS e.g. COVID19.CRUDS"""
        expanded_permissions = {}

        for permission in permissions:
            vaccine_type, operation_codes_str = permission.split(".", maxsplit=1)
            vaccine_type = vaccine_type.lower()
            operation_codes = [
                operation_code
                for operation_code in operation_codes_str.lower()
                if operation_code in list(ApiOperationCode)
            ]
            expanded_permissions[vaccine_type] = operation_codes

        return expanded_permissions

    def _get_supplier_permissions(self, supplier_system: str) -> dict[str, list[ApiOperationCode]]:
        raw_permissions_data = self._cache_client.hget(SUPPLIER_PERMISSIONS_HASH_KEY, supplier_system)
        permissions_data = json.loads(raw_permissions_data) if raw_permissions_data else []

        return self._expand_permissions(permissions_data)

    def authorise(
        self,
        supplier_system: str,
        requested_operation: ApiOperationCode,
        vaccination_types: set[str]
    ) -> bool:
        """Checks that the supplier system is permitted to carry out the requested operation on the given vaccination
        type(s)"""
        supplier_permissions = self._get_supplier_permissions(supplier_system)

        logger.info(
            f"operation: {requested_operation}, supplier_permissions: {supplier_permissions}, "
            f"vaccine_types: {vaccination_types}"
        )
        return all(
            requested_operation in supplier_permissions.get(vaccination_type.lower(), [])
            for vaccination_type in vaccination_types
        )

    def filter_permitted_vacc_types(
        self,
        supplier_system: str,
        requested_operation: ApiOperationCode,
        vaccination_types: set[str]
    ) -> set[str]:
        """Returns the set of vaccine types that a given supplier can interact with for a given operation type.
        This is a more permissive form of authorisation e.g. used in search as it will filter out any requested vacc
        types that they cannot interact with without throwing an error"""
        supplier_permissions = self._get_supplier_permissions(supplier_system)

        return set([
            vaccine_type
            for vaccine_type in vaccination_types
            if requested_operation in supplier_permissions.get(vaccine_type.lower(), [])
        ])
