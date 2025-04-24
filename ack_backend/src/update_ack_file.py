"""Functions for uploading the data to the ack file"""

import json
from io import StringIO, BytesIO
from typing import Union
from botocore.exceptions import ClientError
from constants import (
    ACK_HEADERS,
    SOURCE_BUCKET_NAME,
    ACK_BUCKET_NAME,
    FILE_NAME_PROC_LAMBDA_NAME,
)
from audit_table import (
    change_audit_table_status_to_processed,
    get_next_queued_file_details,
)
from clients import s3_client, logger, lambda_client
from utils_for_ack_lambda import get_row_count


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
        " ".join(
            diagnostics.replace("\r", " ")
            .replace("\n", " ")
            .replace("\t", " ")
            .replace("\xa0", " ")
            .split()
        )
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
            "Success"
            if successful_api_response
            else "Business Level Response Value - Processing Error"
        ),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, use mailbox name if picked up from MESH mail box
        "LOCAL_ID": local_id,
        "IMMS_ID": imms_id or "",
        "OPERATION_OUTCOME": diagnostics or "",
        "MESSAGE_DELIVERY": successful_api_response,
    }


def obtain_current_ack_content(temp_ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = s3_client.get_object(
            Bucket=ACK_BUCKET_NAME, Key=temp_ack_file_key
        )
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
    except ClientError as error:
        # If ack file does not exist in S3 create a new file containing the headers only
        if error.response["Error"]["Code"] in ("404", "NoSuchKey"):
            logger.info("No existing ack file found in S3 - creating new file")
            existing_content = "|".join(ACK_HEADERS) + "\n"
        else:
            logger.error("error whilst obtaining current ack content: %s", error)
            raise

    accumulated_csv_content = StringIO()
    accumulated_csv_content.write(existing_content)
    return accumulated_csv_content


def upload_ack_file(
    temp_ack_file_key: str,
    message_id: str,
    supplier_queue: str,
    accumulated_csv_content: StringIO,
    ack_data_rows: list,
    archive_ack_file_key: str,
    file_key: str,
) -> None:
    """Adds the data row to the uploaded ack file"""
    for row in ack_data_rows:
        data_row_str = [str(item) for item in row.values()]
        cleaned_row = (
            "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
        )
        accumulated_csv_content.write(cleaned_row + "\n")
    csv_file_like_object = BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ACK_BUCKET_NAME, temp_ack_file_key)

    row_count_source = get_row_count(SOURCE_BUCKET_NAME, f"processing/{file_key}")
    row_count_destination = get_row_count(ACK_BUCKET_NAME, temp_ack_file_key)
    # TODO: Should we check for > and if so what handling is required
    if row_count_destination == row_count_source:
        move_file(ACK_BUCKET_NAME, temp_ack_file_key, archive_ack_file_key)
        move_file(SOURCE_BUCKET_NAME, f"processing/{file_key}", f"archive/{file_key}")

        # Update the audit table and invoke the filename lambda with next file in the queue (if one exists)
        change_audit_table_status_to_processed(file_key, message_id)
        next_queued_file_details = get_next_queued_file_details(supplier_queue)
        if next_queued_file_details:
            invoke_filename_lambda(
                next_queued_file_details["filename"],
                next_queued_file_details["message_id"],
            )

    logger.info("Ack file updated to %s: %s", ACK_BUCKET_NAME, archive_ack_file_key)


def update_ack_file(
    file_key: str,
    message_id: str,
    supplier_queue: str,
    created_at_formatted_string: str,
    ack_data_rows: list,
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    ack_filename = (
        f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"
    )
    temp_ack_file_key = f"TempAck/{ack_filename}"
    archive_ack_file_key = f"forwardedFile/{ack_filename}"
    accumulated_csv_content = obtain_current_ack_content(temp_ack_file_key)
    upload_ack_file(
        temp_ack_file_key,
        message_id,
        supplier_queue,
        accumulated_csv_content,
        ack_data_rows,
        archive_ack_file_key,
        file_key,
    )


def move_file(
    bucket_name: str, source_file_key: str, destination_file_key: str
) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)


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
