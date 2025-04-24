"""Utils for filenameprocessor lambda"""

import os
import json
import re
from csv import DictReader
from io import StringIO
from clients import s3_client, lambda_client, logger
from constants import SOURCE_BUCKET_NAME, FILE_NAME_PROC_LAMBDA_NAME


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return (
        _env
        if _env in ["internal-dev", "int", "ref", "sandbox", "prod"]
        else "internal-dev"
    )


def get_csv_content_dict_reader(file_key: str) -> DictReader:
    """Returns the requested file contents from the source bucket in the form of a DictReader"""
    response = s3_client.get_object(
        Bucket=os.getenv("SOURCE_BUCKET_NAME"), Key=file_key
    )
    csv_data = response["Body"].read().decode("utf-8")

    # Verify and process the DAT file content coming from MESH
    if ".dat" in file_key:
        csv_data = extract_content(csv_data)
    return DictReader(StringIO(csv_data), delimiter="|"), csv_data


def create_diagnostics_dictionary(error_type, status_code, error_message) -> dict:
    """Returns a dictionary containing the error_type, statusCode, and error_message"""
    return {
        "error_type": error_type,
        "statusCode": status_code,
        "error_message": error_message,
    }


def invoke_filename_lambda(file_key: str, message_id: str) -> None:
    """Invokes the filenameprocessor lambda with the given file key and message id"""
    try:
        lambda_payload = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": SOURCE_BUCKET_NAME},
                        "object": {"key": file_key},
                    },
                    "message_id": message_id,
                }
            ]
        }
        lambda_client.invoke(
            FunctionName=FILE_NAME_PROC_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(lambda_payload),
        )
    except Exception as error:
        logger.error("Error invoking filename lambda: %s", error)
        raise


def extract_content(dat_file_content):

    boundary_pattern = re.compile(r"----------------------------\d+")

    parts = boundary_pattern.split(dat_file_content)

    # Extract the content between the boundaries
    filecontent = None
    for part in parts:
        if "Content-Disposition" in part and "Content-Type" in part:

            content_start = (
                part.index("Content-Type") + len("Content-Type: text/csv") + 2
            )
            filecontent = part[content_start:].strip()
            break

    return filecontent
