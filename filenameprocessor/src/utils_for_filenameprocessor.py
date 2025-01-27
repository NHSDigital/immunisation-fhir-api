"""Utils for filenameprocessor lambda"""
import json
from csv import DictReader
from io import StringIO
from constants import Constants
from clients import s3_client, logger, lambda_client


def get_created_at_formatted_string(bucket_name: str, file_key: str) -> str:
    """Get the created_at_formatted_string from the response"""
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response["LastModified"].strftime("%Y%m%dT%H%M%S00")


def get_csv_content_dict_reader(bucket_name: str, file_key: str) -> DictReader:
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


def identify_supplier(ods_code: str) -> str:
    """
    Identifies the supplier from the ods code using the mapping.
    Defaults to empty string if ODS code isn't found in the mappings.
    """
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code, "")


def move_file(bucket_name: str, source_key: str, destination_key: str) -> None:

    """     Moves a file from one location to another in S3 by copying and then deleting it.     Args:
    bucket_name (str): Name of the S3 bucket.         source_key (str): Source file key.
    destination_key (str): Destination file key."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_key},
        Key=destination_key
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_key)
    logger.info("File moved from %s to %s", source_key, destination_key)


def invoke_filename_lambda(file_name_processor_name, source_bucket_name, file_key, message_id):
    lambda_payload = {"Records": [
        {
            "s3": {
                "bucket": {
                    "name": source_bucket_name
                },
                "object": {
                    "key": file_key
                }
            },
            "message_id": message_id}
            ]
        }
    lambda_client.invoke(
        FunctionName=file_name_processor_name,
        InvocationType="Event",
        Payload=json.dumps(lambda_payload))
