from clients import redis_client
from models.constants import Constants
import json

def get_supplier_permissions(supplier: str) -> list[str]:
    permissions_data = redis_client.hget(Constants.SUPPLIER_PERMISSIONS_KEY, supplier)
    if not permissions_data:
        return []
    return json.loads(permissions_data)
