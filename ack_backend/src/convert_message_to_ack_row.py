"""Functions for converting the incoming message body into a row of ack data"""

from typing import Union
from logging_decorators import convert_messsage_to_ack_row_logging_decorator
from update_ack_file import create_ack_data


def get_error_message_for_ack_file(message_diagnostics) -> Union[None, str]:
    """Determines and returns the error message to be displayed in the ack file"""
    if message_diagnostics is None:
        return None

    if not isinstance(message_diagnostics, dict):
        return "Unable to determine diagnostics issue"

    if message_diagnostics.get("statusCode") in (None, 500):
        return "An unhandled error occurred during batch processing"

    return message_diagnostics.get("error_message", "Unable to determine diagnostics issue")


@convert_messsage_to_ack_row_logging_decorator
def convert_message_to_ack_row(message, created_at_formatted_string):
    """
    Takes a single message and returns the ack data row for that message.
    A value error is raised if the file_key or created_at_formatted_string for the message do not match the
    expected values.
    """
    diagnostics = message.get("diagnostics")
    return create_ack_data(
        created_at_formatted_string=created_at_formatted_string,
        local_id=message.get("local_id"),
        row_id=message.get("row_id"),
        successful_api_response=diagnostics is None,  # Response is successful if and only if there are no diagnostics
        diagnostics=get_error_message_for_ack_file(diagnostics),
        imms_id=message.get("imms_id"),
    )
