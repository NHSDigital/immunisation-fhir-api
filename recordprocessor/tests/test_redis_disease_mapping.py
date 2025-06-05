import unittest
from unittest.mock import patch, MagicMock
from src.redis_disease_mapping import DiseaseMapping
from src.redis_cacher import RedisCacher
from src.constants import DISEASE_MAPPING_FILE_KEY


class TestDiseaseMapping(unittest.TestCase):

    basic_cache = {
                 "vaccine": {
                     "vac1": {"diseases": ["lurgy1"]}},
                 "disease": {
                     "lurgy1": {}}
                 }

    def setUp(self):
        # Patch redis.StrictRedis
        self.strict_redis_patcher = patch("src.redis_cacher.redis.StrictRedis")
        self.strict_redis = self.strict_redis_patcher.start()
        self.mock_redis_client = MagicMock()
        self.strict_redis.return_value = self.mock_redis_client

        # Patch logger methods
        self.logger_info_patcher = patch("src.redis_cacher.logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("src.redis_cacher.logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.logger_warning_patcher = patch("src.redis_cacher.logger.warning")
        self.mock_logger_warning = self.logger_warning_patcher.start()

        # Create a RedisCacher instance (mocked)
        self.mock_redis_client.ping.return_value = True
        self.redis_cacher = RedisCacher("localhost", 6379)

    def tearDown(self):
        self.strict_redis_patcher.stop()
        self.logger_info_patcher.stop()
        self.logger_exception_patcher.stop()
        self.logger_warning_patcher.stop()

    def test_get_cache_called(self):
        self.redis_cacher.get_cache = MagicMock(return_value=self.basic_cache)
        DiseaseMapping(self.redis_cacher)
        self.redis_cacher.get_cache.assert_called_once_with(DISEASE_MAPPING_FILE_KEY)

    def test_get_diseases_returns_expected_dict(self):
        self.redis_cacher.get_cache = MagicMock(return_value=self.basic_cache)
        mapping = DiseaseMapping(self.redis_cacher)
        diseases = mapping.get_diseases("vac1")
        self.assertEqual(diseases, ["lurgy1"])

    def test_get_vaccines_returns_expected(self):
        self.redis_cacher.get_cache = MagicMock(return_value=self.basic_cache)
        mapping = DiseaseMapping(self.redis_cacher)
        vaccines = mapping.get_vaccines("lurgy1")
        self.assertEqual(vaccines, ["vac1"])


if __name__ == "__main__":
    unittest.main()
