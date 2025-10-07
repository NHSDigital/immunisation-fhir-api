import json
from clients import redis_client
from constants import (
    VACCINE_TYPE_TO_DISEASES_HASH_KEY,
    SUPPLIER_PERMISSIONS_HASH_KEY,
    ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY
)


def get_supplier_permissions_from_cache(supplier_system: str) -> list[str]:
    """Gets and returns the permissions config file content from ElastiCache (Redis)."""
    permissions_str = redis_client.hget(SUPPLIER_PERMISSIONS_HASH_KEY, supplier_system)
    return json.loads(permissions_str) if permissions_str else []


def get_valid_vaccine_types_from_cache() -> list[str]:
    return redis_client.hkeys(VACCINE_TYPE_TO_DISEASES_HASH_KEY)


def get_supplier_system_from_cache(ods_code: str) -> str:
    return redis_client.hget(ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY, ods_code)
