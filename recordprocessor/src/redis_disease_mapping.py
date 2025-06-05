"Upload the content from a config file in S3 to ElastiCache (Redis)"

from redis_cacher import RedisCacher

from constants import DISEASE_MAPPING_FILE_KEY


class DiseaseMapping:
    """Class to handle disease mapping operations."""

    def __init__(self, redis_cache: RedisCacher):
        self.redis_cache = redis_cache

    def get_disease_mapping(self) -> dict:
        """Gets and returns the disease mapping file from ElastiCache (Redis)."""
        ret = self.redis_cache.get_cache(DISEASE_MAPPING_FILE_KEY)
        return ret
