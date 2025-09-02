"""Utils for filenameprocessor lambda"""

import os
from csv import DictReader
from io import TextIOWrapper
from clients import s3_client, logger


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(file_key: str) -> DictReader:
    """Returns the requested file contents from the source bucket in the form of a DictReader"""
    logger.info("SAW> get_csv_content_dict_reader..1")
    response = s3_client.get_object(Bucket=os.getenv("SOURCE_BUCKET_NAME"), Key=file_key)
    logger.info("SAW> get_csv_content_dict_reader..2")
    binary_io = response["Body"]
    logger.info("SAW> get_csv_content_dict_reader..3")
    text_io = TextIOWrapper(binary_io, encoding="utf-8", newline="")
    logger.info("SAW> get_csv_content_dict_reader..4")
    return DictReader(text_io, delimiter="|")


def create_diagnostics_dictionary(error_type, status_code, error_message) -> dict:
    """Returns a dictionary containing the error_type, statusCode, and error_message"""
    return {"error_type": error_type, "statusCode": status_code, "error_message": error_message}
