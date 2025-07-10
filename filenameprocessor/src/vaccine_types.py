import json
from clients import redis_client
from constants import VACCINE_TYPE_TO_DISEASES_HASH_KEY

def get_valid_vaccine_types_from_cache() -> list[str]:
    return redis_client.hkeys(VACCINE_TYPE_TO_DISEASES_HASH_KEY)