from redis_client import redis_client
import json

def get_supplier_permissions(supplier: str) -> list[str]:
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    if not permissions_data:
        return []
    return json.loads(permissions_data)
