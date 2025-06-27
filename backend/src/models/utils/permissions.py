from clients import redis_client
import json


def get_supplier_permissions(supplier: str) -> list[str]:
    print(f"Getting permissions for supplier: {supplier}")
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    print(f"Got permissions: {permissions_data}")
    if not permissions_data:
        return []
    return json.loads(permissions_data)
