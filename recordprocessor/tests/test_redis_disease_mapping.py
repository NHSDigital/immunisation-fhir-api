import unittest
from src.redis_disease_mapping import DiseaseMapping
from constants import DISEASE_MAPPING_FILE_KEY
from redis_cacher import RedisCacher


class TestDiseaseMapping(unittest.TestCase):
    def setUp(self):
        host = "immunisation-redis-cluster.0y9mwl.0001.euw2.cache.amazonaws.com"
        redis_client = RedisCacher(host, 6379)
        
        # CLI
        # redis-cli -h immunisation-redis-cluster.0y9mwl.0001.euw2.cache.amazonaws.com -p 6379
        
        self.disease_mapping = DiseaseMapping(redis_client)

    def test_get_disease_mapping_returns_expected_dict(self):
        expected = {"disease": "measles"}

        result = self.disease_mapping.get_disease_mapping()

        self.assertEqual(result, expected)

    def test_get_disease_mapping_returns_empty_dict(self):
        self.mock_redis_cache.get_cache.return_value = {}

        result = self.disease_mapping.get_disease_mapping()

        self.mock_redis_cache.get_cache.assert_called_once_with(DISEASE_MAPPING_FILE_KEY)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()