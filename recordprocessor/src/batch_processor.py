"""Application to convert rows from batch files to FHIR and forward to Kinesis for further downstream processing"""

import json
import os
import time

from constants import FileStatus
from process_row import process_row
from mappings import map_target_disease
from audit_table import update_audit_table_status
from send_to_kinesis import send_to_kinesis
from clients import logger
from file_level_validation import file_level_validation, get_csv_content_dict_reader
from errors import NoOperationPermissions, InvalidHeaders


def process_csv_to_fhir(incoming_message_body: dict, encoding="utf-8", start_row=0) -> None:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """
    try:
        interim_message_body = file_level_validation(incoming_message_body=incoming_message_body,
                                                     encoding=encoding)
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
        for row in csv_reader:
            if row_count >= start_row:
                row_count += 1
                row_id = f"{file_id}^{row_count}"
                logger.info("MESSAGE ID : %s", row_id)
                # concat dict to string for logging
                # row_str = ", ".join(f"{v}" for k, v in row.items())
                # print(f"Processing row {row_count}: {row_str[:20]}")

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

                logger.info("Total rows processed: %s", row_count)
    except Exception as error:  # pylint: disable=broad-exception-caught
        # encoder = "latin-1"
        encoder = "cp1252"
        print(f"Error processing: {error}.")
        print(f"Encode error at row {row_count} with {encoding}. Switch to {encoder}")
        # if we are here, re-read the file with correct encoding and ignore the processed rows
        # if error.args[0] == "'utf-8' codec can't decode byte 0xe9 in position 2996: invalid continuation byte":
        # cp1252
        new_reader = get_csv_content_dict_reader(file_key, encoding=encoder)
        start_row = row_count
        row_count = 0
        for row in new_reader:
            row_count += 1
            if row_count > start_row:
                row_id = f"{file_id}^{row_count}"
                logger.info("MESSAGE ID : %s", row_id)
                original_representation = ", ".join(f"{v}" for k, v in row.items())
                if original_representation[:20] == "9473089333, DORTHY, ":
                    print(f"Processing row {row_count}: {original_representation[:40]}")

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

                logger.info("Total rows processed: %s", row_count)

    update_audit_table_status(file_key, file_id, FileStatus.PREPROCESSED)


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    start = time.time()
    try:
        # SAW - error thrown here when invalid character using windows-1252
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
    end = time.time()
    logger.info("Total time for completion: %ss", round(end - start, 5))


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
