"""Utils functions for filenameprocessor tests"""

from unittest.mock import patch
from io import StringIO
import json

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from csv import DictReader


def get_csv_file_dict_reader(s3_client, bucket_name: str, file_key: str) -> DictReader:
    """Download the file from the S3 bucket and return it as a DictReader"""
    ack_file_csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


def generate_permissions_config_content(permissions_dict: dict) -> str:
    """Converts the permissions dictionary to a JSON string of the permissions config file content"""
    return json.dumps({"all_permissions": permissions_dict})
