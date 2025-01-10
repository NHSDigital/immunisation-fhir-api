"""Utils for filenameprocessor lambda"""

import os
from csv import DictReader
from io import StringIO
from clients import s3_client


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(file_key: str) -> DictReader:
    """Returns the requested file contents from the source bucket in the form of a DictReader"""
    response = s3_client.get_object(Bucket=os.getenv("SOURCE_BUCKET_NAME"), Key=file_key)
    csv_data = response["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_data), delimiter="|"), csv_data


def create_diagnostics_dictionary(error_type, status_code, error_message) -> dict:
    """Returns a dictionary containing the error_type, statusCode, and error_message"""
    return {"error_type": error_type, "statusCode": status_code, "error_message": error_message}
