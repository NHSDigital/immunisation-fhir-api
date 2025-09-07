"""Application to convert rows from batch files to FHIR and forward to Kinesis for further downstream processing"""

import json
import os
import time
from process_row import process_row
from mappings import map_target_disease
from send_to_kinesis import send_to_kinesis
from clients import logger
from file_level_validation import file_level_validation, validate_content_headers
from errors import NoOperationPermissions, InvalidHeaders, InvalidEncoding
from utils_for_recordprocessor import get_csv_content_dict_reader


def process_csv_to_fhir(incoming_message_body: dict) -> None:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """
    encoder = "utf-8"  # default encoding
    try:
        interim_message_body = file_level_validation(incoming_message_body=incoming_message_body, encoder=encoder)
    except InvalidEncoding as error:
        logger.warning("Invalid Encoding detected in process_csv_to_fhir: %s", error)
        # retry with cp1252 encoding
        encoder = "cp1252"
        try:
            interim_message_body = file_level_validation(incoming_message_body=incoming_message_body, encoder=encoder)
        except Exception as error:
            logger.error(f"Error in file_level_validation with {encoder} encoding: %s", error)
            return 0
    except (InvalidHeaders, NoOperationPermissions, Exception):  # pylint: disable=broad-exception-caught
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
        print(f"Error processing: {err}.")
        # check if it's a decode error, ie error.args[0] begins with "'utf-8' codec can't decode byte"
        if err.reason == "invalid continuation byte":
            new_encoder = "cp1252"
            print(f"Encode error at row {row_count} with {encoder}. Switch to {new_encoder}")
            # print(f"Detected decode error: {error.reason}")
            encoder = new_encoder
            # if we are here, re-read the file with alternative encoding and skip processed rows
            csv_reader = get_csv_content_dict_reader(file_key, encoder=encoder)
            validate_content_headers(csv_reader)
            row_count = process_rows(file_id, vaccine, supplier, file_key, allowed_operations,
                                     created_at_formatted_string, csv_reader, target_disease, row_count)
        else:
            logger.error(f"Non-decode error: {err}. Cannot retry. Call someone.")
            raise err

    logger.info("Total rows processed: %s", row_count)
    return row_count


def process_rows_retry(file_id, vaccine, supplier, file_key, allowed_operations,
                       created_at_formatted_string, encoder, total_rows_processed_count=0) -> int:
    """
    Retry processing rows with a different encoding from a specific row number
    """
    print("process_rows_retry...")
    new_reader = get_csv_content_dict_reader(file_key, encoder=encoder)

    total_rows_processed_count = process_rows(
        file_id, vaccine, supplier, file_key, allowed_operations,
        created_at_formatted_string, new_reader, total_rows_processed_count)

    return total_rows_processed_count


def process_rows(file_id, vaccine, supplier, file_key, allowed_operations, created_at_formatted_string,
                 csv_reader, target_disease,
                 total_rows_processed_count=0) -> int:
    """
    Processes each row in the csv_reader starting from start_row.
    """
    print("process_rows...")
    row_count = 0
    start_row = total_rows_processed_count
    try:
        for row in csv_reader:

            row_count += 1
            if row_count > start_row:
                row_id = f"{file_id}^{row_count}"
                logger.info("MESSAGE ID : %s", row_id)

                # convert dict to string and print first 20 chars
                if (total_rows_processed_count % 1000 == 0):
                    print(f"Process: {total_rows_processed_count}")
                if (total_rows_processed_count > 19995):
                    print(f"Process: {total_rows_processed_count} - {row['PERSON_SURNAME']}")

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
                logger.info("Total rows processed: %s", total_rows_processed_count)
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing row %s: %s", row_count, error)
        return total_rows_processed_count, error
    return total_rows_processed_count


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
