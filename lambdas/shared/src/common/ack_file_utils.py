"""Create ack file and upload to S3 bucket"""

import json
from csv import writer
from io import BytesIO, StringIO

from common.clients import get_s3_client
from common.models.batch_constants import ACK_BUCKET_NAME, TEMP_ACK_DIR


def make_ack_data(
    message_id: str,
    validation_passed: bool,
    message_delivered: bool,
    created_at_formatted_string: str,
) -> dict:
    """Returns a dictionary of ack data based on the input values. Dictionary keys are the ack file headers,
    dictionary values are the values for the ack file row"""
    success_display = "Success"
    failure_display = "Infrastructure Level Response Value - Processing Error"
    return {
        "MESSAGE_HEADER_ID": message_id,
        "HEADER_RESPONSE_CODE": ("Success" if (validation_passed and message_delivered) else "Failure"),
        "ISSUE_SEVERITY": "Information" if validation_passed else "Fatal",
        "ISSUE_CODE": "OK" if validation_passed else "Fatal Error",
        "ISSUE_DETAILS_CODE": "20013" if validation_passed else "10001",
        "RESPONSE_TYPE": "Technical",
        "RESPONSE_CODE": ("20013" if (validation_passed and message_delivered) else "10002"),
        "RESPONSE_DISPLAY": (success_display if (validation_passed and message_delivered) else failure_display),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, add mailbox if from mesh mailbox
        "LOCAL_ID": "",  # TODO: Leave blank for DPS, add from ctl file if data picked up from MESH mailbox
        "MESSAGE_DELIVERY": message_delivered,
    }


def upload_ack_file(file_key: str, ack_data: dict, created_at_formatted_string: str) -> None:
    """Formats the ack data into a csv file and uploads it to the ack bucket"""
    ack_filename = "ack/" + file_key.replace(".csv", f"_InfAck_{created_at_formatted_string}.csv")

    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = writer(csv_buffer, delimiter="|")
    csv_writer.writerow(list(ack_data.keys()))
    csv_writer.writerow(list(ack_data.values()))

    # Upload the CSV file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    get_s3_client().upload_fileobj(csv_bytes, ACK_BUCKET_NAME, ack_filename)


def create_json_ack_file(
    message_id: str,
    file_key: str,
    created_at_formatted_string: str,
) -> None:
    if file_key is None:
        return
    """Creates the initial JSON BusAck file and uploads it to the temp bucket"""
    ack_filename = TEMP_ACK_DIR + "/" + file_key.replace(".csv", f"_BusAck_{created_at_formatted_string}.json")
    raw_ack_filename = ack_filename.split(".")[0]
    try:
        provider = ack_filename.split("_")[3]
    except IndexError:
        provider = "unknown"

    # Generate the initial fields
    ack_data_dict = {}
    ack_data_dict["system"] = "Immunisation FHIR API Batch Report"
    ack_data_dict["version"] = 1  # TO FIX

    ack_data_dict["generatedDate"] = ""  # will be filled on completion
    ack_data_dict["filename"] = raw_ack_filename
    ack_data_dict["provider"] = provider
    ack_data_dict["messageHeaderId"] = message_id

    ack_data_dict["summary"] = {}
    ack_data_dict["failures"] = []

    print(json.dumps(ack_data_dict, indent=2))

    # Upload ack_data_dict to S3
    json_bytes = BytesIO(json.dumps(ack_data_dict, indent=2).encode("utf-8"))
    get_s3_client().upload_fileobj(json_bytes, ACK_BUCKET_NAME, ack_filename)


def make_and_upload_ack_file(
    message_id: str,
    file_key: str,
    validation_passed: bool,
    message_delivered: bool,
    created_at_formatted_string: str,
) -> None:
    """Creates the ack file and uploads it to the S3 ack bucket"""
    ack_data = make_ack_data(message_id, validation_passed, message_delivered, created_at_formatted_string)
    upload_ack_file(file_key, ack_data, created_at_formatted_string)
