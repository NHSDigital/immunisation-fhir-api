"""Tests for elasticache functions"""
import json
from unittest import TestCase
from unittest.mock import patch
from boto3 import client as boto3_client
from moto import mock_s3

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from tests.utils_for_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from elasticache import get_supplier_permissions_from_cache, get_valid_vaccine_types_from_cache
    from clients import REGION_NAME

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

    @patch("elasticache.redis_client.hget", return_value=json.dumps(["COVID19.CRUDS", "RSV.CRUDS"]))
    def test_get_supplier_permissions_from_cache(self, mock_hget):
        result = get_supplier_permissions_from_cache("TEST_SUPPLIER")
        self.assertEqual(result, ["COVID19.CRUDS", "RSV.CRUDS"])
        mock_hget.assert_called_once_with("supplier_permissions", "TEST_SUPPLIER")

    @patch("elasticache.redis_client.hget", return_value=None)
    def test_get_supplier_permissions_from_cache_not_found(self, mock_hget):
        result = get_supplier_permissions_from_cache("TEST_SUPPLIER")
        self.assertEqual(result, [])
        mock_hget.assert_called_once_with("supplier_permissions", "TEST_SUPPLIER")

    @patch("elasticache.redis_client.hkeys", return_value=["COVID19", "RSV", "FLU"])
    def test_get_valid_vaccine_types_from_cache(self, mock_hkeys):
        result = get_valid_vaccine_types_from_cache()
        self.assertEqual(result, ["COVID19", "RSV", "FLU"])
        mock_hkeys.assert_called_once_with("vacc_to_diseases")
