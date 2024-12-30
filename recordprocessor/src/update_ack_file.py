"""Functions for adding a row of data to the ack file"""

from io import StringIO, BytesIO
import os
from typing import Union
from clients import s3_client
from utils_for_recordprocessor import get_environment


def create_ack_data(
    created_at_formatted_string: str,
    row_id: str,
    delivered: bool,
    diagnostics: Union[None, str],
    imms_id: Union[None, str],
) -> dict:
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "OK" if (delivered and not diagnostics) else "Fatal Error",
        "ISSUE_SEVERITY": "Information" if not diagnostics else "Fatal",
        "ISSUE_CODE": "OK" if not diagnostics else "Fatal Error",
        "ISSUE_DETAILS_CODE": "30001" if not diagnostics else "30002",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30001" if (delivered and not diagnostics) else "30002",
        "RESPONSE_DISPLAY": (
            "Success" if (delivered and not diagnostics) else "Business Level Response Value - Processing Error"
        ),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, use mailbox name if picked up from MESH mail box
        "LOCAL_ID": "",  # TODO: Leave blank for DPS, obtain from ctl file if picked up from MESH mail box
        "IMMS_ID": imms_id or "",
        "OPERATION_OUTCOME": diagnostics or "",
        "MESSAGE_DELIVERY": delivered,
    }


def add_row_to_ack_file(ack_data: dict, accumulated_ack_file_content: StringIO, file_key: str) -> StringIO:
    """Adds the data row to the uploaded ack file"""
    data_row_str = [str(item) for item in ack_data.values()]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
    accumulated_ack_file_content.write(cleaned_row + "\n")
    csv_file_like_object = BytesIO(accumulated_ack_file_content.getvalue().encode("utf-8"))
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-destinations")
    ack_filename = f"processedFile/{file_key.replace('.csv', '_response.csv')}"
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    return accumulated_ack_file_content


def update_ack_file(
    file_key: str,
    bucket_name: str,
    accumulated_ack_file_content: StringIO,
    row_id: str,
    message_delivered: bool,
    diagnostics: Union[None, str],
    imms_id: Union[None, str],
) -> StringIO:
    """Updates the ack file with the new data row based on the given arguments"""
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")
    ack_data_row = create_ack_data(created_at_formatted_string, row_id, message_delivered, diagnostics, imms_id)
    accumulated_ack_file_content = add_row_to_ack_file(ack_data_row, accumulated_ack_file_content, file_key)
    return accumulated_ack_file_content
