"""Functions for adding a row of data to the ack file"""

import os
import json
from io import StringIO, BytesIO
from typing import Union
from botocore.exceptions import ClientError
from constants import Constants
from audit_table import update_audit_table_status, get_queued_file_details
from clients import s3_client, logger, lambda_client
#TODO move to constants
ENVIRONMENT = os.getenv("ENVIRONMENT")
SOURCE_BUCKET_NAME = f"immunisation-batch-{ENVIRONMENT}-data-sources"
FILE_NAME_PROC_LAMBDA_NAME = os.getenv("FILE_NAME_PROC_LAMBDA_NAME")

def create_ack_data(
    created_at_formatted_string: str,
    local_id: str,
    row_id: str,
    successful_api_response: bool,
    diagnostics: Union[None, str] = None,
    imms_id: str = None,
) -> dict:
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    # Pack multi-line diagnostics down to single line (because Imms API diagnostics may be multi-line)
    diagnostics = (
        " ".join(diagnostics.replace("\r", " ").replace("\n", " ").replace("\t", " ").replace("\xa0", " ").split())
        if diagnostics is not None
        else None
    )
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "OK" if successful_api_response else "Fatal Error",
        "ISSUE_SEVERITY": "Information" if not diagnostics else "Fatal",
        "ISSUE_CODE": "OK" if not diagnostics else "Fatal Error",
        "ISSUE_DETAILS_CODE": "30001" if not diagnostics else "30002",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30001" if successful_api_response else "30002",
        "RESPONSE_DISPLAY": (
            "Success" if successful_api_response else "Business Level Response Value - Processing Error"
        ),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, use mailbox name if picked up from MESH mail box
        "LOCAL_ID": local_id,
        "IMMS_ID": imms_id or "",
        "OPERATION_OUTCOME": diagnostics or "",
        "MESSAGE_DELIVERY": successful_api_response,
    }


def obtain_current_ack_content(ack_bucket_name: str, ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    accumulated_csv_content = StringIO()
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_file_key)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        accumulated_csv_content.write(existing_content)
    except ClientError as error:
        if error.response["Error"]["Code"] in ("404", "NoSuchKey"):
            logger.info("No existing ack file found in S3 - creating new file")
            # If ack file does not exist in S3 create a new file
            accumulated_csv_content.write("|".join(Constants.ack_headers) + "\n")
        else:
            logger.error("error whilst obtaining current ack content:%s", error)
            raise
    return accumulated_csv_content


def upload_ack_file(
    ack_bucket_name: str, ack_file_key: str, accumulated_csv_content: StringIO, ack_data_row: any, row_count: int, archive_ack_file_key: str, file_key: str
    , created_at_formatted_string: str
) -> None:
    """Adds the data row to the uploaded ack file"""
    for row in ack_data_row:
        data_row_str = [str(item) for item in row.values()]
        cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
        accumulated_csv_content.write(cleaned_row + "\n")
    csv_file_like_object = BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_file_key)
    row_count_dest = get_row_count_stream(ack_bucket_name, ack_file_key)
    if row_count == row_count_dest:
        move_file(ack_bucket_name, ack_file_key, archive_ack_file_key)
        source_key = f"processing/{file_key}"
        destination_key = f"archive/{file_key}"
        move_file(SOURCE_BUCKET_NAME, source_key, destination_key)
        queue_name = update_audit_table_status(file_key)
        file_key, message_id = get_queued_file_details(queue_name)
        if file_key and message_id is not None:
            # Directly invoke the Lambda function
            invoke_filename_lambda(SOURCE_BUCKET_NAME, file_key, message_id)
        
    logger.info("Ack file updated to %s: %s", ack_bucket_name, archive_ack_file_key)


def update_ack_file(
    file_key: str,
    created_at_formatted_string: str,
    ack_data_rows: any,
    row_count
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    ack_file_key = f"TempAck/{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"
    archive_ack_file_key = f"forwardedFile/{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME")
    accumulated_csv_content = obtain_current_ack_content(ack_bucket_name, ack_file_key)
    upload_ack_file(ack_bucket_name, ack_file_key, accumulated_csv_content, ack_data_rows, row_count, archive_ack_file_key, file_key, created_at_formatted_string)

def get_row_count_stream(bucket_name, key):
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    count = sum(1 for _ in response['Body'].iter_lines())
    return count

def move_file(bucket_name: str, source_key: str, destination_key: str) -> None:

    """     Moves a file from one location to another in S3 by copying and then deleting it.     
            Args: bucket_name (str): Name of the S3 bucket.         
            source_key (str): Source file key.         
            destination_key (str): Destination file key.     
    """
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_key},
        Key=destination_key
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_key)
    logger.info("File moved from %s to %s", source_key, destination_key)


def invoke_filename_lambda(source_bucket_name, file_key, message_id):
    lambda_payload = {"Records":[
            {
            "s3": {
                "bucket": {
                    "name": source_bucket_name
                },
                "object": {
                    "key": file_key
                }
            },
            "message_id": message_id
            }
        ]
        }
    lambda_client.invoke(
        FunctionName=FILE_NAME_PROC_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps(lambda_payload))