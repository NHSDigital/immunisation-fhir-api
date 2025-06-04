"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
from clients import redis_client
from constants import DISEASE_MAPPING_FILE_KEY


def get_disease_mapping_json_from_cache() -> dict:
    """Gets and returns the disease mapping file from ElastiCache (Redis)."""
    
    return json.loads(redis_client.get(DISEASE_MAPPING_FILE_KEY))
