"""Application to convert rows from batch files to FHIR and forward to Kinesis for further downstream processing"""

import json
import os
import time
from process_row import process_row
from mappings import map_target_disease
from send_to_kinesis import send_to_kinesis
from clients import logger
from file_level_validation import file_level_validation
from errors import NoOperationPermissions, InvalidHeaders
from utils_for_recordprocessor import get_csv_content_dict_reader
from typing import Optional


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
    except (InvalidHeaders, NoOperationPermissions, Exception) as e:  # pylint: disable=broad-exception-caught
        logger.error(f"File level validation failed: {e}")
        # If the file is invalid, processing should cease immediately
        return 0

    file_id = interim_message_body.get("message_id")
    vaccine = interim_message_body.get("vaccine")
    supplier = interim_message_body.get("supplier")
    file_key = interim_message_body.get("file_key")
    allowed_operations = interim_message_body.get("allowed_operations")
    created_at_formatted_string = interim_message_body.get("created_at_formatted_string")
    csv_reader = interim_message_body.get("csv_dict_reader")

    target_disease = map_target_disease(vaccine)
    row_count = 0
    row_count, err = process_rows(file_id, vaccine, supplier, file_key, allowed_operations,
                                  created_at_formatted_string, csv_reader, target_disease)

    if err:
        if isinstance(err, UnicodeDecodeError):
            """ resolves encoding issue VED-754 """
            logger.warning(f"Encoding Error: {err}.")
            new_encoder = "cp1252"
            logger.info(f"Encode error at row {row_count} with {encoder}. Switch to {new_encoder}")
            encoder = new_encoder
            # load alternative encoder
            csv_reader = get_csv_content_dict_reader(f"processing/{file_key}", encoder=encoder)
            # re-read the file and skip processed rows
            row_count, err = process_rows(file_id, vaccine, supplier, file_key, allowed_operations,
                                          created_at_formatted_string, csv_reader, target_disease, row_count)
        else:
            logger.error(f"Row Processing error: {err}")
            raise err

    return row_count


def process_rows(file_id, vaccine, supplier, file_key, allowed_operations, created_at_formatted_string,
                 csv_reader, target_disease,
                 total_rows_processed_count=0) -> tuple[int, Optional[Exception]]:
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
                    logger.info(f"Process: {total_rows_processed_count+1}")
                if start_row > 0 and row_count <= start_row+10:
                    logger.info(f"Restarted Process (log up to first 10): {total_rows_processed_count+1}")

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
        n_rows_processed = process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
    end = time.time()
    logger.info("Total rows processed: %s", n_rows_processed)
    logger.info("Total time for completion: %ss", round(end - start, 5))


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
