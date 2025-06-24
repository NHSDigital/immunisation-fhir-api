from clients import redis_client
from errors import VaccineTypePermissionsError
import json

def get_supplier_permissions(supplier: str) -> list[str]:
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    if not permissions_data:
        return []
    return json.loads(permissions_data)
