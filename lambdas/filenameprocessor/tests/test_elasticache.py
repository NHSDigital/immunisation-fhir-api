"""Tests for elasticache functions"""

import json
from unittest import TestCase
from unittest.mock import Mock, patch

from boto3 import client as boto3_client
from moto import mock_s3

from utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from utils_for_tests.utils_for_filenameprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    create_mock_hget,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from elasticache import (
        get_supplier_permissions_from_cache,
        get_supplier_system_from_cache,
        get_valid_vaccine_types_from_cache,
    )

s3_client = boto3_client("s3", region_name=REGION_NAME)


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@patch("elasticache.get_redis_client")
class TestElasticache(TestCase):
    """Tests for elasticache functions"""

    def setUp(self):
        """Set up the S3 buckets"""
        GenericSetUp(s3_client)

    def tearDown(self):
        """Tear down the S3 buckets"""
        GenericTearDown(s3_client)

    def test_get_supplier_system_from_cache(self, mock_get_redis_client):
        mock_redis = Mock()
        mock_redis.hget.side_effect = create_mock_hget({"TEST_ODS_CODE": "TEST_SUPPLIER"}, {})
        mock_get_redis_client.return_value = mock_redis

        result = get_supplier_system_from_cache("TEST_ODS_CODE")
        self.assertEqual(result, "TEST_SUPPLIER")
        mock_redis.hget.assert_called_once_with("ods_code_to_supplier", "TEST_ODS_CODE")

    def test_get_supplier_permissions_from_cache(self, mock_get_redis_client):
        mock_redis = Mock()
        mock_redis.hget.side_effect = create_mock_hget({}, {"TEST_SUPPLIER": json.dumps(["COVID19.CRUDS", "RSV.CRUDS"])})
        mock_get_redis_client.return_value = mock_redis

        result = get_supplier_permissions_from_cache("TEST_SUPPLIER")
        self.assertEqual(result, ["COVID19.CRUDS", "RSV.CRUDS"])
        mock_redis.hget.assert_called_once_with("supplier_permissions", "TEST_SUPPLIER")

    def test_get_supplier_permissions_from_cache_not_found(self, mock_get_redis_client):
        mock_redis = Mock()
        mock_redis.hget.side_effect = create_mock_hget({}, {})
        mock_get_redis_client.return_value = mock_redis

        result = get_supplier_permissions_from_cache("TEST_SUPPLIER")
        self.assertEqual(result, [])
        mock_redis.hget.assert_called_once_with("supplier_permissions", "TEST_SUPPLIER")

    def test_get_valid_vaccine_types_from_cache(self, mock_get_redis_client):
        mock_redis = Mock()
        mock_redis.hkeys.return_value = ["COVID19", "RSV", "FLU"]
        mock_get_redis_client.return_value = mock_redis

        result = get_valid_vaccine_types_from_cache()
        self.assertEqual(result, ["COVID19", "RSV", "FLU"])
        mock_redis.hkeys.assert_called_once_with("vacc_to_diseases")
