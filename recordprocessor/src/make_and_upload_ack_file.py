"""Create ack file and upload to S3 bucket"""

from csv import writer
from io import StringIO, BytesIO
from clients import s3_client
from constants import ACK_BUCKET_NAME


def make_ack_data(
    message_id: str,
    validation_passed: bool,
    message_delivered: bool,
    created_at_formatted_string,
) -> dict:
    """Returns a dictionary of ack data based on the input values. Dictionary keys are the ack file headers,
    dictionary values are the values for the ack file row"""
    success_display = "Success"
    failure_display = "Infrastructure Level Response Value - Processing Error"
    return {
        "MESSAGE_HEADER_ID": message_id,
        "HEADER_RESPONSE_CODE": (
            "Success" if (validation_passed and message_delivered) else "Failure"
        ),
        "ISSUE_SEVERITY": "Information" if validation_passed else "Fatal",
        "ISSUE_CODE": "OK" if validation_passed else "Fatal Error",
        "ISSUE_DETAILS_CODE": "20013" if validation_passed else "10001",
        "RESPONSE_TYPE": "Technical",
        "RESPONSE_CODE": (
            "20013" if (validation_passed and message_delivered) else "10002"
        ),
        "RESPONSE_DISPLAY": (
            success_display
            if (validation_passed and message_delivered)
            else failure_display
        ),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, add mailbox if from mesh mailbox
        "LOCAL_ID": "",  # TODO: Leave blank for DPS, add from ctl file if data picked up from MESH mailbox
        "MESSAGE_DELIVERY": message_delivered,
    }


def upload_ack_file(
    file_key: str, ack_data: dict, created_at_formatted_string: str
) -> None:
    """Formats the ack data into a csv file and uploads it to the ack bucket"""
    ack_filename = "ack/" + file_key.replace(
        ".csv", f"_InfAck_{created_at_formatted_string}.csv"
    )

    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = writer(csv_buffer, delimiter="|")
    csv_writer.writerow(list(ack_data.keys()))
    csv_writer.writerow(list(ack_data.values()))

    # Upload the CSV file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_bytes, ACK_BUCKET_NAME, ack_filename)


def make_and_upload_ack_file(
    message_id: str,
    file_key: str,
    validation_passed: bool,
    message_delivered: bool,
    created_at_formatted_string: str,
) -> None:
    """Creates the ack file and uploads it to the S3 ack bucket"""
    ack_data = make_ack_data(
        message_id, validation_passed, message_delivered, created_at_formatted_string
    )
    upload_ack_file(file_key, ack_data, created_at_formatted_string)
