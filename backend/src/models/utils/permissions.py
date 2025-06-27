# from clients import redis_client
import json
import redis

from src.clients import REDIS_HOST, REDIS_PORT


def get_supplier_permissions(supplier: str) -> list[str]:
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
    redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print(f"Getting permissions for supplier: {supplier}")
    permissions_data = redis_client.hget("supplier_permissions", supplier)
    print(f"Got permissions: {permissions_data}")
    if not permissions_data:
        return []
    return json.loads(permissions_data)
