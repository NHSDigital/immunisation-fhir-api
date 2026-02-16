"""Functions for uploading the data to the ack file"""

import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO

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
    BATCH_FILE_ARCHIVE_DIR,
    BATCH_FILE_PROCESSING_DIR,
    BATCH_REPORT_TITLE,
    BATCH_REPORT_VERSION,
    COMPLETED_ACK_DIR,
    DEFAULT_STREAM_NAME,
    LAMBDA_FUNCTION_NAME_PREFIX,
    TEMP_ACK_DIR,
)

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", DEFAULT_STREAM_NAME)


def _generated_date() -> str:
    return datetime.now(timezone.utc).isoformat()[:-13] + ".000Z"


def _create_ack_data_dict() -> dict:
    return {
        "failures": [],
    }


def _complete_ack_data_dict(
    existing_ack_data_dict: dict,
    supplier: str,
    raw_ack_filename: str,
    message_id: str,
    total_ack_rows_processed: int,
    successful_record_count: int,
    total_failures: int,
    ingestion_start_time: int,
    ingestion_end_time: int,
) -> dict:
    return {
        "system": BATCH_REPORT_TITLE,
        "version": BATCH_REPORT_VERSION,
        "generatedDate": _generated_date(),
        "provider": supplier,
        "filename": raw_ack_filename,
        "messageHeaderId": message_id,
        "summary": {
            "totalRecords": total_ack_rows_processed,
            "succeeded": successful_record_count,
            "failed": total_failures,
            "ingestionTime": {
                "start": ingestion_start_time,
                "end": ingestion_end_time,
            },
        },
        "failures": deepcopy(existing_ack_data_dict["failures"]),
    }


def _make_ack_data_row(ack_data_row: dict) -> dict:
    return {
        "rowId": int(ack_data_row["MESSAGE_HEADER_ID"].split("^")[-1]),
        "responseCode": ack_data_row["RESPONSE_CODE"],
        "responseDisplay": ack_data_row["RESPONSE_DISPLAY"],
        "severity": ack_data_row["ISSUE_SEVERITY"],
        "localId": ack_data_row["LOCAL_ID"],
        "operationOutcome": ack_data_row["OPERATION_OUTCOME"],
    }


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

    move_file(SOURCE_BUCKET_NAME, f"{BATCH_FILE_PROCESSING_DIR}/{file_key}", f"{BATCH_FILE_ARCHIVE_DIR}/{file_key}")

    total_ack_rows_processed, total_failures = get_record_count_and_failures_by_message_id(message_id)
    successful_record_count = total_ack_rows_processed - total_failures

    # Consider creating time utils and using datetime instead of time
    time_now = time.gmtime(time.time())
    ingestion_end_time = time.strftime("%Y%m%dT%H%M%S00", time_now)
    update_audit_table_item(
        file_key=file_key,
        message_id=message_id,
        attrs_to_update={
            AuditTableKeys.RECORDS_SUCCEEDED: successful_record_count,
            AuditTableKeys.INGESTION_END_TIME: ingestion_end_time,
            AuditTableKeys.STATUS: FileStatus.PROCESSED,
        },
    )

    # finish JSON file
    ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.json')}"
    temp_ack_file_key = f"{TEMP_ACK_DIR}/{ack_filename}"
    ack_data_dict = obtain_current_ack_content(temp_ack_file_key)

    ack_data_dict = _complete_ack_data_dict(
        existing_ack_data_dict=ack_data_dict,
        supplier=supplier,
        raw_ack_filename=file_key.split(".")[0],
        message_id=message_id,
        total_ack_rows_processed=total_ack_rows_processed,
        successful_record_count=successful_record_count,
        total_failures=total_failures,
        ingestion_start_time=get_ingestion_start_time_by_message_id(message_id),
        ingestion_end_time=int(time.strftime("%s", time_now)),
    )

    # Upload ack_data_dict to S3
    json_bytes = BytesIO(json.dumps(ack_data_dict, indent=2).encode("utf-8"))
    get_s3_client().upload_fileobj(json_bytes, ACK_BUCKET_NAME, temp_ack_file_key)
    move_file(ACK_BUCKET_NAME, f"{TEMP_ACK_DIR}/{ack_filename}", f"{COMPLETED_ACK_DIR}/{ack_filename}")

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


def obtain_current_ack_content(temp_ack_file_key: str) -> dict:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = get_s3_client().get_object(Bucket=ACK_BUCKET_NAME, Key=temp_ack_file_key)
    except ClientError as error:
        # If ack file does not exist in S3 create a new file containing the headers only
        if error.response["Error"]["Code"] in ("404", "NoSuchKey"):
            logger.info("No existing JSON ack file found in S3 - creating new file")

            # Generate the initial fields
            return _create_ack_data_dict()
        else:
            logger.error("error whilst obtaining current JSON ack content: %s", error)
            raise

    return json.loads(existing_ack_file["Body"].read().decode("utf-8"))


def update_ack_file(
    file_key: str,
    created_at_formatted_string: str,
    ack_data_rows: list,
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    if ack_data_rows:
        ack_filename = f"{file_key.replace('.csv', f'_BusAck_{created_at_formatted_string}.json')}"
        temp_ack_file_key = f"{TEMP_ACK_DIR}/{ack_filename}"
        ack_data_dict = obtain_current_ack_content(temp_ack_file_key)

        for row in ack_data_rows:
            ack_data_dict["failures"].append(_make_ack_data_row(row))

        # Upload ack_data_dict to S3
        json_bytes = BytesIO(json.dumps(ack_data_dict, indent=2).encode("utf-8"))
        get_s3_client().upload_fileobj(json_bytes, ACK_BUCKET_NAME, temp_ack_file_key)
        logger.info("JSON ack file updated to %s: %s", ACK_BUCKET_NAME, temp_ack_file_key)
