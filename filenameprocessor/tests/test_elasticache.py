"""Tests for elasticache functions"""

from unittest import TestCase
from unittest.mock import patch
import fakeredis
from boto3 import client as boto3_client
from moto import mock_s3

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames
from tests.utils_for_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from elasticache import upload_to_elasticache, get_permissions_config_json_from_cache
    from clients import REGION_NAME
    from constants import PERMISSIONS_CONFIG_FILE_KEY

s3_client = boto3_client("s3", region_name=REGION_NAME)


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestElasticache(TestCase):
    """Tests for elasticache functions"""

    def setUp(self):
        """Set up the S3 buckets"""
        GenericSetUp(s3_client)

    def tearDown(self):
        """Tear down the S3 buckets"""
        GenericTearDown(s3_client)

    def test_permissions_caching(self):
        """
        Test that upload_to_elasticache successfully uploads the file to elasticache, which is then successfully read
        by get_permissions_config_json_from_cache
        """
        mock_permissions_1 = {"test_supplier_1": ["RSV_FULL"], "test_supplier_2": ["FLU_CREATE", "FLU_UPDATE"]}
        mock_permissions_config_1 = generate_permissions_config_content(mock_permissions_1)

        mock_permissions_2 = {
            "test_supplier_1": ["FLU_FULL"],
            "test_supplier_2": ["RSV_CREATE"],
            "test_supplier_3": ["RSV_UPDATE"],
        }
        mock_permissions_config_2 = generate_permissions_config_content(mock_permissions_2)

        with patch("elasticache.redis_client", fakeredis.FakeStrictRedis()):
            # Test that the permissions config is successfully uploaded to elasticache
            s3_client.put_object(
                Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY, Body=mock_permissions_config_1
            )
            upload_to_elasticache(PERMISSIONS_CONFIG_FILE_KEY, BucketNames.CONFIG)
            self.assertEqual(get_permissions_config_json_from_cache(), {"all_permissions": mock_permissions_1})

            # Test that the cache is updated with the new permissions config
            s3_client.put_object(
                Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY, Body=mock_permissions_config_2
            )
            upload_to_elasticache(PERMISSIONS_CONFIG_FILE_KEY, BucketNames.CONFIG)
            self.assertEqual(get_permissions_config_json_from_cache(), {"all_permissions": mock_permissions_2})
