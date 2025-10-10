"""Create ack file and upload to S3 bucket"""

from csv import writer
import os
from io import StringIO, BytesIO
from clients import s3_client


def make_the_ack_data(message_id: str, message_delivered: bool, created_at_formatted_string: str) -> dict:
    """
    Returns a dictionary of ack data based on the input values.
    Dictionary keys are the ack file headers, dictionary values are the values for the ack file row
    """
    failure_display = "Infrastructure Level Response Value - Processing Error"
    return {
        "MESSAGE_HEADER_ID": message_id,
        "HEADER_RESPONSE_CODE": "Failure",
        "ISSUE_SEVERITY": "Fatal",
        "ISSUE_CODE": "Fatal Error",
        "ISSUE_DETAILS_CODE": "10001",
        "RESPONSE_TYPE": "Technical",
        "RESPONSE_CODE": "10002",
        "RESPONSE_DISPLAY": failure_display,
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
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME")
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)


def make_and_upload_the_ack_file(
    message_id: str,
    file_key: str,
    message_delivered: bool,
    created_at_formatted_string: str,
) -> None:
    """Creates the ack file and uploads it to the S3 ack bucket"""
    ack_data = make_the_ack_data(message_id, message_delivered, created_at_formatted_string)
    upload_ack_file(file_key, ack_data, created_at_formatted_string)
