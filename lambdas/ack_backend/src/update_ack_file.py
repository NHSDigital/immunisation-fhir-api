"""Functions for uploading the data to the ack file"""

import json
import os
import time
from datetime import datetime
from io import BytesIO, StringIO

from botocore.exceptions import ClientError

from common.aws_s3_utils import move_file
from common.batch.audit_table import (
    get_ingestion_start_time_by_message_id,
    get_record_count_and_failures_by_message_id,
    update_audit_table_item,
)
from common.clients import get_s3_client, logger
from common.log_decorator import generate_and_send_logs
from common.models.batch_constants import (
    ACK_BUCKET_NAME,
    SOURCE_BUCKET_NAME,
    AuditTableKeys,
    FileStatus,
)
from constants import (
    ACK_HEADERS,
    BATCH_FILE_ARCHIVE_DIR,
    BATCH_FILE_PROCESSING_DIR,
    COMPLETED_ACK_DIR,
    DEFAULT_STREAM_NAME,
    LAMBDA_FUNCTION_NAME_PREFIX,
    TEMP_ACK_DIR,
)

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", DEFAULT_STREAM_NAME)


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


def complete_batch_file_process(
    message_id: str,
    supplier: str,
    vaccine_type: str,
    created_at_formatted_string: str,
    file_key: str,
) -> dict:
    """Mark the batch file as processed. This involves moving the ack and original file to destinations and updating
    the audit table status"""
    start_time = time.time()

    # finish CSV file
    ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"

    move_file(ACK_BUCKET_NAME, f"{TEMP_ACK_DIR}/{ack_filename}", f"{COMPLETED_ACK_DIR}/{ack_filename}")
    move_file(SOURCE_BUCKET_NAME, f"{BATCH_FILE_PROCESSING_DIR}/{file_key}", f"{BATCH_FILE_ARCHIVE_DIR}/{file_key}")

    total_ack_rows_processed, total_failures = get_record_count_and_failures_by_message_id(message_id)
    update_audit_table_item(
        file_key=file_key, message_id=message_id, attrs_to_update={AuditTableKeys.STATUS: FileStatus.PROCESSED}
    )

    # Consider creating time utils and using datetime instead of time
    time_now = time.gmtime(time.time())
    ingestion_end_time = time.strftime("%Y%m%dT%H%M%S00", time_now)
    ingestion_end_time_seconds = int(time.strftime("%s", time_now))
    successful_record_count = total_ack_rows_processed - total_failures
    update_audit_table_item(
        file_key=file_key,
        message_id=message_id,
        attrs_to_update={
            AuditTableKeys.RECORDS_SUCCEEDED: successful_record_count,
            AuditTableKeys.INGESTION_END_TIME: ingestion_end_time,
        },
    )

    # finish JSON file
    json_ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.json')}"
    temp_ack_file_key = f"{TEMP_ACK_DIR}/{json_ack_filename}"
    ack_data_dict = obtain_current_json_ack_content(message_id, temp_ack_file_key)

    generated_date = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ack_data_dict["generatedDate"] = generated_date
    ack_data_dict["provider"] = supplier
    ack_data_dict["summary"]["totalRecords"] = total_ack_rows_processed
    ack_data_dict["summary"]["success"] = successful_record_count
    ack_data_dict["summary"]["failed"] = total_failures
    ack_data_dict["summary"]["ingestionTime"]["end"] = ingestion_end_time_seconds

    # Upload ack_data_dict to S3
    json_bytes = BytesIO(json.dumps(ack_data_dict, indent=2).encode("utf-8"))
    get_s3_client().upload_fileobj(json_bytes, ACK_BUCKET_NAME, temp_ack_file_key)
    move_file(ACK_BUCKET_NAME, f"{TEMP_ACK_DIR}/{json_ack_filename}", f"{COMPLETED_ACK_DIR}/{json_ack_filename}")

    result = {
        "message_id": message_id,
        "file_key": file_key,
        "supplier": supplier,
        "vaccine_type": vaccine_type,
        "row_count": total_ack_rows_processed,
        "success_count": successful_record_count,
        "failure_count": total_failures,
    }

    log_batch_file_process(
        start_time=start_time,
        result=result,
        function_name=f"{LAMBDA_FUNCTION_NAME_PREFIX}_complete_batch_file_process",
    )

    return result


def log_batch_file_process(start_time: float, result: dict, function_name: str) -> None:
    """Logs the batch file processing completion to Splunk"""
    base_log_data = {
        "function_name": function_name,
        "date_time": str(datetime.now()),
        **result,
    }
    additional_log_data = {
        "status": "success",
        "statusCode": 200,
        "message": "Record processing complete",
    }
    generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data)


def obtain_current_ack_content(temp_ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = get_s3_client().get_object(Bucket=ACK_BUCKET_NAME, Key=temp_ack_file_key)
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


def obtain_current_json_ack_content(message_id: str, temp_ack_file_key: str) -> dict:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = get_s3_client().get_object(Bucket=ACK_BUCKET_NAME, Key=temp_ack_file_key)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        ack_data_dict = json.loads(existing_content)
    except ClientError as error:
        # If ack file does not exist in S3 create a new file containing the headers only
        if error.response["Error"]["Code"] in ("404", "NoSuchKey"):
            logger.info("No existing JSON ack file found in S3 - creating new file")

            ingestion_start_time = get_ingestion_start_time_by_message_id(message_id)
            raw_ack_filename = temp_ack_file_key.split(".")[0]

            # Generate the initial fields
            ack_data_dict = {}
            ack_data_dict["system"] = "Immunisation FHIR API Batch Report"
            ack_data_dict["version"] = 1  # TO FIX

            ack_data_dict["generatedDate"] = ""  # will be filled on completion
            ack_data_dict["provider"] = ""  # will be filled on completion
            ack_data_dict["filename"] = raw_ack_filename
            ack_data_dict["messageHeaderId"] = message_id

            ack_data_dict["summary"] = {}
            ack_data_dict["summary"]["ingestionTime"] = {}
            ack_data_dict["summary"]["ingestionTime"]["start"] = ingestion_start_time
            ack_data_dict["failures"] = []
        else:
            logger.error("error whilst obtaining current JSON ack content: %s", error)
            raise

    return ack_data_dict


def update_ack_file(
    file_key: str,
    created_at_formatted_string: str,
    ack_data_rows: list,
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.csv')}"
    temp_ack_file_key = f"{TEMP_ACK_DIR}/{ack_filename}"
    accumulated_csv_content = obtain_current_ack_content(temp_ack_file_key)

    for row in ack_data_rows:
        data_row_str = [str(item) for item in row.values()]
        cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
        accumulated_csv_content.write(cleaned_row + "\n")

    csv_file_like_object = BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))

    get_s3_client().upload_fileobj(csv_file_like_object, ACK_BUCKET_NAME, temp_ack_file_key)
    logger.info("Ack file updated to %s: %s", ACK_BUCKET_NAME, temp_ack_file_key)


def update_json_ack_file(
    message_id: str,
    file_key: str,
    created_at_formatted_string: str,
    ack_data_rows: list,
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.json')}"
    temp_ack_file_key = f"{TEMP_ACK_DIR}/{ack_filename}"
    ack_data_dict = obtain_current_json_ack_content(message_id, temp_ack_file_key)

    for row in ack_data_rows:
        json_data_row = {}
        json_data_row["rowId"] = row["MESSAGE_HEADER_ID"].split("^")[-1]
        json_data_row["responseCode"] = row["RESPONSE_CODE"]
        json_data_row["responseDisplay"] = row["RESPONSE_DISPLAY"]
        json_data_row["severity"] = row["ISSUE_SEVERITY"]
        json_data_row["localId"] = row["LOCAL_ID"]
        json_data_row["operationOutcome"] = row["OPERATION_OUTCOME"]

        ack_data_dict["failures"].append(json_data_row)

    # Upload ack_data_dict to S3
    json_bytes = BytesIO(json.dumps(ack_data_dict, indent=2).encode("utf-8"))
    get_s3_client().upload_fileobj(json_bytes, ACK_BUCKET_NAME, temp_ack_file_key)
    logger.info("JSON ack file updated to %s: %s", ACK_BUCKET_NAME, temp_ack_file_key)
