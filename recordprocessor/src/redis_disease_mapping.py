"Upload the content from a config file in S3 to ElastiCache (Redis)"

import json
import redis
from constants import DISEASE_MAPPING_FILE_KEY


class RedisCacher():
    """ RedisCacher abstraction class to decouple application code
    from direct use of Redis client."""

    def __init__(self, redis_host, redis_port, logger):
        try:
            # Attempt to connect to Redis
            self.redis_client = redis.StrictRedis(redis_host, redis_port, decode_responses=True)
            # Check the connection with a PING command
            if self.redis_client.ping():
                logger.info("Successfully connected to Redis.")
            else:
                logger.error("Failed to connect to Redis.")
        except Exception as e:
            logger.exception(f"Connection to Redis failed: {e}")

    def get(self, key: str) -> dict:
        """Gets the value from Redis cache for the given key."""
        value = self.redis_client.get(key)
        if value is not None:
            return json.loads(value)
        return {}


class DiseaseMapping:
    """Class to handle disease mapping operations."""
    # redis_cache instance is found in clients.py
    def __init__(self, redis_cache: RedisCacher):
        mapping = redis_cache.get(DISEASE_MAPPING_FILE_KEY)
        self.vaccines = mapping["vaccine"]
        self.diseases = mapping["disease"]
        self.load_vaccines_into_diseases()
        self.vaccine_mapp = self.load_simple_vaccine_map()

    def load_simple_vaccine_map(self) -> dict:
        """Load a simple vaccine map for quick access."""
        vaccine_map = {}
        for vaccine, details in self.vaccines.items():
            # set key as vaccine name and value as list of diseases
            # if details do not contain diseases, set it to an empty list
            if not isinstance(details, dict):
                continue
            diseases = details.get("diseases", [])
            if not isinstance(diseases, list):
                diseases = []
            vaccine_map[vaccine] = diseases
        return vaccine_map        

    def load_vaccines_into_diseases(self):
        """Load vaccines into diseases for easier access."""
        # loop through vaccines, identify diseases, and add them to the disease map
        for vaccine, details in self.vaccines.items():
            diseases = details.get("diseases", [])
            for disease in diseases:
                if disease not in self.diseases:
                    self.diseases[disease] = {"vaccines": []}
                # if vaccines key does not exist, create it
                if "vaccines" not in self.diseases[disease]:
                    self.diseases[disease]["vaccines"] = []
                # if vaccine not in the disease's vaccines, add it
                if vaccine not in self.diseases[disease]["vaccines"]:
                    self.diseases[disease]["vaccines"].append(vaccine)

    def get_diseases_from_vaccine(self, vaccine: str) -> list:
        """Returns a list of diseases for the given vaccine."""
        vaccine = self.vaccines.get(vaccine, {})
        if not vaccine:
            return []
        return vaccine.get("diseases", [])

    def get_vaccines_from_disease(self, disease: str) -> list:
        """Returns a list of vaccines for the given disease."""
        disease = self.disease_map.get(disease, {})
        if not disease:
            return []
        return disease.get("vaccines", [])

    def get_vaccine_map(self) -> dict:
        """Returns the vaccine map."""
        return self.vaccine_map
