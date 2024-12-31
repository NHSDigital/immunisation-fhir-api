"""Utils functions for filenameprocessor tests"""

from io import StringIO
import json
from csv import DictReader


def download_csv_file_as_dict_reader(s3_client, bucket_name: str, file_key: str) -> DictReader:
    """Download the file from the S3 bucket and return it as a DictReader"""
    ack_file_csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


def generate_permissions_config_content(permissions_dict: dict) -> str:
    """Converts the permissions dictionary to a JSON string"""
    return json.dumps({"all_permissions": permissions_dict})
