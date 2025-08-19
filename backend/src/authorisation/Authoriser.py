import json

from authorisation.ApiOperationCode import ApiOperationCode
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

    def _get_supplier_permissions(self, supplier_name: str) -> dict[str, list[ApiOperationCode]]:
        raw_permissions_data = self._cache_client.hget(SUPPLIER_PERMISSIONS_HASH_KEY, supplier_name)
        permissions_data = json.loads(raw_permissions_data) if raw_permissions_data else []

        return self._expand_permissions(permissions_data)

    def authorise(
        self,
        supplier_name: str,
        requested_operation: ApiOperationCode,
        vaccination_types: set[str]
    ) -> bool:
        supplier_permissions = self._get_supplier_permissions(supplier_name)

        logger.info(
            f"operation: {requested_operation}, supplier_permissions: {supplier_permissions}, "
            f"vaccine_types: {vaccination_types}"
        )
        return all(
            requested_operation in supplier_permissions.get(vaccination_type.lower(), [])
            for vaccination_type in vaccination_types
        )
