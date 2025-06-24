from clients import redis_client
from errors import VaccineTypePermissionsError
import json

def get_supplier_permissions(supplier: str) -> list[str]:
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    if not permissions_data:
        return []
    return json.loads(permissions_data)

def validate_vaccine_type_permissions(vaccine_type: str, supplier: str):
    permissions = get_supplier_permissions(supplier)
    if not any(vaccine_type in perm for perm in permissions):
        raise VaccineTypePermissionsError(f"{supplier} is not allowed to access {vaccine_type}")