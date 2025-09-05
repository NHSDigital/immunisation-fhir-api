"""Utils for filenameprocessor lambda"""

import os
from csv import DictReader
from io import TextIOWrapper
from clients import s3_client


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(file_key: str, encoding="utf-8") -> DictReader:
    """Returns the requested file contents from the source bucket in the form of a DictReader"""
    response = s3_client.get_object(Bucket=os.getenv("SOURCE_BUCKET_NAME"), Key=file_key)
    binary_io = response["Body"]
    text_io = TextIOWrapper(binary_io, encoding=encoding, newline="")
    return DictReader(text_io, delimiter="|")


def create_diagnostics_dictionary(error_type, status_code, error_message) -> dict:
    """Returns a dictionary containing the error_type, statusCode, and error_message"""
    return {"error_type": error_type, "statusCode": status_code, "error_message": error_message}


def fix_cp1252_text(text: str, encoder: str, decoder: str) -> str:
    raw_bytes = text.encode(encoder, errors='replace')  # Or 'latin-1' if needed
    corrected_text = raw_bytes.decode(decoder, errors='replace')
    return corrected_text


def dict_decode(source_dict: dict, decoder: str) -> dict:
    """Decode all string values in a dictionary from one encoding to another."""

    return {k: v.decode(decoder) if isinstance(v, bytes) else v for k, v in source_dict.items()}
