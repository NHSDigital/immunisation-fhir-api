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


def process_csv_to_fhir(incoming_message_body: dict) -> None:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """
    try:
        interim_message_body = file_level_validation(incoming_message_body=incoming_message_body)
    except (InvalidHeaders, NoOperationPermissions, Exception):  # pylint: disable=broad-exception-caught
        # If the file is invalid, processing should cease immediately
        return

    file_id = interim_message_body.get("message_id")
    vaccine = interim_message_body.get("vaccine")
    supplier = interim_message_body.get("supplier")
    file_key = interim_message_body.get("file_key")
    allowed_operations = interim_message_body.get("allowed_operations")
    created_at_formatted_string = interim_message_body.get("created_at_formatted_string")
    csv_reader = interim_message_body.get("csv_dict_reader")

    target_disease = map_target_disease(vaccine)
    row_count = 0
    try:
        row_count = process_rows(file_id, vaccine, supplier, file_key, allowed_operations,
                                 created_at_formatted_string, csv_reader, target_disease)
    except Exception as error:  # pylint: disable=broad-exception-caught
        encoder = "cp1252"
        print(f"Error processing: {error}.")
        print(f"Encode error at row {row_count} with {encoding}. Switch to {encoder}")
        # check if it's a decode error, ie error.args[0] begins with "'utf-8' codec can't decode byte"
        if error.args[0].startswith("'utf-8' codec can't decode byte"):
            print(f"Detected decode error: {error.args[0]}")
            # if we are here, re-read the file with correct encoding and ignore the processed rows
            # if error.args[0] == "'utf-8' codec can't decode byte 0xe9 in position 2996: invalid continuation byte":
            # cp1252
            row_count += process_rows_retry(file_id, vaccine, supplier, file_key,
                                            allowed_operations, created_at_formatted_string,
                                            "cp1252", start_row=row_count)
        else:
            logger.error(f"Non-decode error: {error}. Cannot retry.")
            raise error from error

    logger.info("Total rows processed: %s", row_count)
    update_audit_table_status(file_key, file_id, FileStatus.PREPROCESSED)


def process_rows_retry(file_id, vaccine, supplier, file_key, allowed_operations,
                       created_at_formatted_string, encoder, target_disease, start_row=0) -> int:
    new_reader = get_csv_content_dict_reader(file_key, encoding=encoder)
    return process_rows(file_id, vaccine, supplier, file_key, allowed_operations,
                        created_at_formatted_string, new_reader, start_row)


def process_rows(file_id, vaccine, supplier, file_key, allowed_operations, created_at_formatted_string,
                 csv_reader, target_disease, start_row=0) -> int:
    """
    Processes each row in the csv_reader starting from start_row.
    """

    row_count = 0
    for row in csv_reader:
        if row_count >= start_row:
            row_count += 1
            row_id = f"{file_id}^{row_count}"
            logger.info("MESSAGE ID : %s", row_id)

            details_from_processing = process_row(target_disease, allowed_operations, row)

            outgoing_message_body = {
                "row_id": row_id,
                "file_key": file_key,
                "supplier": supplier,
                "vax_type": vaccine,
                "created_at_formatted_string": created_at_formatted_string,
                **details_from_processing,
            }

            send_to_kinesis(supplier, outgoing_message_body, vaccine)

    return row_count


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    start = time.time()
    try:
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
    end = time.time()
    logger.info("Total time for completion: %ss", round(end - start, 5))


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
