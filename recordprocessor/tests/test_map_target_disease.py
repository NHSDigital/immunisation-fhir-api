"""Tests for map_target_disease"""
import json
import unittest
from unittest.mock import patch
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from mappings import map_target_disease


@patch("mappings.redis_client")
class TestMapTargetDisease(unittest.TestCase):
    """
    Test that map_target_disease returns the correct target disease element for valid vaccine types, or [] for
    invalid vaccine types.
    """

    def test_map_target_disease_valid(self, mock_redis_client):
        """Tests map_target_disease returns the disease coding information when using valid vaccine types"""
        mock_redis_client.hget.return_value = json.dumps([{
            "code": "55735004",
            "term": "Respiratory syncytial virus infection (disorder)"
        }])

        self.assertEqual(map_target_disease("RSV"), [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "55735004",
                "display": "Respiratory syncytial virus infection (disorder)"
            }]
        }])

        mock_redis_client.hget.assert_called_with("vacc-to-diseases", "RSV")

    def test_map_target_disease_invalid(self, mock_redis_client):
        """Tests map_target_disease does not return the disease coding information when using invalid vaccine types."""

        mock_redis_client.hget.return_value = None

        self.assertEqual(map_target_disease("invalid_vaccine"), [])

        mock_redis_client.hget.assert_called_with("vacc-to-diseases", "invalid_vaccine")


if __name__ == "__main__":
    unittest.main()
