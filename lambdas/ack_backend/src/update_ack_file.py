"""Functions for uploading the data to the ack file"""

from botocore.exceptions import ClientError
from io import StringIO, BytesIO
from typing import Optional
from audit_table import change_audit_table_status_to_processed
from common.clients import get_s3_client, logger
from constants import ACK_HEADERS, get_source_bucket_name, get_ack_bucket_name
from logging_decorators import upload_ack_file_logging_decorator
from utils_for_ack_lambda import get_row_count


def create_ack_data(
    created_at_formatted_string: str,
    local_id: str,
    row_id: str,
    successful_api_response: bool,
    diagnostics: None | str = None,
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


def obtain_current_ack_content(temp_ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = get_s3_client().get_object(Bucket=get_ack_bucket_name(), Key=temp_ack_file_key)
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


@upload_ack_file_logging_decorator
def upload_ack_file(
    temp_ack_file_key: str,
    message_id: str,
    supplier: str,
    vaccine_type: str,
    accumulated_csv_content: StringIO,
    ack_data_rows: list,
    archive_ack_file_key: str,
    file_key: str,
) -> Optional[dict]:
    """Adds the data row to the uploaded ack file"""
    for row in ack_data_rows:
        data_row_str = [str(item) for item in row.values()]
        cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
        accumulated_csv_content.write(cleaned_row + "\n")
    csv_file_like_object = BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))

    ack_bucket_name = get_ack_bucket_name()
    source_bucket_name = get_source_bucket_name()

    get_s3_client().upload_fileobj(csv_file_like_object, ack_bucket_name, temp_ack_file_key)

    row_count_source = get_row_count(source_bucket_name, f"processing/{file_key}")
    row_count_destination = get_row_count(ack_bucket_name, temp_ack_file_key)
    # TODO: Should we check for > and if so what handling is required
    if row_count_destination == row_count_source:
        move_file(ack_bucket_name, temp_ack_file_key, archive_ack_file_key)
        move_file(source_bucket_name, f"processing/{file_key}", f"archive/{file_key}")

        # Update the audit table
        change_audit_table_status_to_processed(file_key, message_id)

        # Ingestion of this file is complete
        result = {
            "message_id": message_id,
            "file_key": file_key,
            "supplier": supplier,
            "vaccine_type": vaccine_type,
            "row_count": row_count_source - 1,
        }
    else:
        result = None
    logger.info("Ack file updated to %s: %s", ack_bucket_name, archive_ack_file_key)
    return result


def update_ack_file(
    file_key: str,
    message_id: str,
    supplier: str,
    vaccine_type: str,
    created_at_formatted_string: str,
    ack_data_rows: list,
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"
    temp_ack_file_key = f"TempAck/{ack_filename}"
    archive_ack_file_key = f"forwardedFile/{ack_filename}"
    accumulated_csv_content = obtain_current_ack_content(temp_ack_file_key)
    upload_ack_file(
        temp_ack_file_key,
        message_id,
        supplier,
        vaccine_type,
        accumulated_csv_content,
        ack_data_rows,
        archive_ack_file_key,
        file_key,
    )


def move_file(bucket_name: str, source_file_key: str, destination_file_key: str) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client = get_s3_client()
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)
