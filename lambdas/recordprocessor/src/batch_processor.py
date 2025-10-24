"""Application to convert rows from batch files to FHIR and forward to Kinesis for further downstream processing"""

import json
import os
import time
from csv import DictReader
from json import JSONDecodeError
from typing import Optional

from audit_table import update_audit_table_status
from common.clients import logger
from constants import (
    ARCHIVE_DIR_NAME,
    PROCESSING_DIR_NAME,
    SOURCE_BUCKET_NAME,
    FileNotProcessedReason,
    FileStatus,
)
from file_level_validation import file_is_empty, file_level_validation, move_file
from mappings import map_target_disease
from process_row import process_row
from send_to_kinesis import send_to_kinesis
from utils_for_recordprocessor import get_csv_content_dict_reader


def process_csv_to_fhir(incoming_message_body: dict) -> int:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    Returns the number of rows processed. While this is not used by the handler, the number of rows
    processed must be correct and therefore is returned for logging and test purposes.
    """
    encoder = "utf-8"  # default encoding
    try:
        incoming_message_body["encoder"] = encoder
        interim_message_body = file_level_validation(incoming_message_body=incoming_message_body)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"File level validation failed: {e}")  # If the file is invalid, processing should cease
        return 0

    file_id = interim_message_body.get("message_id")
    vaccine = interim_message_body.get("vaccine")
    supplier = interim_message_body.get("supplier")
    file_key = interim_message_body.get("file_key")
    allowed_operations = interim_message_body.get("allowed_operations")
    created_at_formatted_string = interim_message_body.get("created_at_formatted_string")
    csv_reader = interim_message_body.get("csv_dict_reader")

    target_disease = map_target_disease(vaccine)

    row_count, err = process_rows(
        file_id,
        vaccine,
        supplier,
        file_key,
        allowed_operations,
        created_at_formatted_string,
        csv_reader,
        target_disease,
    )

    if err:
        if isinstance(err, UnicodeDecodeError):
            """resolves encoding issue VED-754"""
            logger.warning(f"Encoding Error: {err}.")
            new_encoder = "cp1252"
            logger.info(f"Encode error at row {row_count} with {encoder}. Switch to {new_encoder}")
            encoder = new_encoder

            # load alternative encoder
            csv_reader = get_csv_content_dict_reader(f"{PROCESSING_DIR_NAME}/{file_key}", encoder=encoder)
            # re-read the file and skip processed rows
            row_count, err = process_rows(
                file_id,
                vaccine,
                supplier,
                file_key,
                allowed_operations,
                created_at_formatted_string,
                csv_reader,
                target_disease,
                row_count,
            )
        else:
            logger.error(f"Row Processing error: {err}")
            raise err

    file_status = FileStatus.PREPROCESSED

    if file_is_empty(row_count):
        logger.warning("File was empty: %s. Moving file to archive directory.", file_key)
        move_file(
            SOURCE_BUCKET_NAME,
            f"{PROCESSING_DIR_NAME}/{file_key}",
            f"{ARCHIVE_DIR_NAME}/{file_key}",
        )
        file_status = f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.EMPTY}"

    update_audit_table_status(file_key, file_id, file_status, record_count=row_count)
    return row_count


# Process the row to obtain the details needed for the message_body and ack file
def process_rows(
    file_id: str,
    vaccine: str,
    supplier: str,
    file_key: str,
    allowed_operations: set,
    created_at_formatted_string: str,
    csv_reader: DictReader,
    target_disease: list[dict],
    total_rows_processed_count: int = 0,
) -> tuple[int, Optional[Exception]]:
    """
    Processes each row in the csv_reader starting from start_row.
    """
    row_count = 0
    start_row = total_rows_processed_count
    try:
        for row in csv_reader:
            row_count += 1
            if row_count > start_row:
                row_id = f"{file_id}^{row_count}"
                logger.info("MESSAGE ID : %s", row_id)
                # Log progress every 1000 rows and the first 10 rows after a restart
                if total_rows_processed_count % 1000 == 0:
                    logger.info(f"Process: {total_rows_processed_count + 1}")
                if start_row > 0 and row_count <= start_row + 10:
                    logger.info(f"Restarted Process (log up to first 10): {total_rows_processed_count + 1}")
                # Process the row to obtain the details needed for the message_body and ack file
                details_from_processing = process_row(target_disease, allowed_operations, row)
                # Create the message body for sending
                outgoing_message_body = {
                    "row_id": row_id,
                    "file_key": file_key,
                    "supplier": supplier,
                    "vax_type": vaccine,
                    "created_at_formatted_string": created_at_formatted_string,
                    **details_from_processing,
                }
                send_to_kinesis(supplier, outgoing_message_body, vaccine)
                total_rows_processed_count += 1
    except UnicodeDecodeError as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing row %s: %s", row_count, error)
        return total_rows_processed_count, error

    return total_rows_processed_count, None


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    start = time.time()
    n_rows_processed = 0

    try:
        incoming_message_body = json.loads(event)
    except JSONDecodeError as error:
        logger.error("Error decoding incoming message: %s", error)
        return

    try:
        n_rows_processed = process_csv_to_fhir(incoming_message_body=incoming_message_body)
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
        message_id = incoming_message_body.get("message_id")
        file_key = incoming_message_body.get("file_key")

        # If an unexpected error occurs, attempt to mark the event as failed. If the event is so malformed that this
        # also fails, we will still get the error alert and the event will remain in processing meaning the supplier +
        # vacc type queue is blocked until we resolve the issue
        update_audit_table_status(file_key, message_id, FileStatus.FAILED, error_details=str(error))

    end = time.time()
    logger.info("Total rows processed: %s", n_rows_processed)
    logger.info("Total time for completion: %ss", round(end - start, 5))


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
