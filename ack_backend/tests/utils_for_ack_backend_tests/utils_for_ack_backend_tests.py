"""Utils functions for the ack backend tests"""

import json
from boto3 import client as boto3_client
from tests.utils_for_ack_backend_tests.values_for_ack_backend_tests import ValidValues, MOCK_MESSAGE_DETAILS
from tests.utils_for_ack_backend_tests.mock_environment_variables import REGION_NAME, BucketNames

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)


def generate_event(test_messages: list[dict]) -> dict:
    """
    Returns an event where each message in the incoming message body list is based on a standard mock message,
    updated with the details from the corresponsing message in the given test_messages list.
    """
    incoming_message_body = [
        (
            {**MOCK_MESSAGE_DETAILS.failure_message, **message}
            if message.get("diagnostics")
            else {**MOCK_MESSAGE_DETAILS.success_message, **message}
        )
        for message in test_messages
    ]
    return {"Records": [{"body": json.dumps(incoming_message_body)}]}


def setup_existing_ack_file(file_key, file_content):
    """Uploads an existing file with the given content."""
    s3_client.put_object(Bucket=BucketNames.DESTINATION, Key=file_key, Body=file_content)


def obtain_current_ack_file_content(temp_ack_file_key: str = MOCK_MESSAGE_DETAILS.temp_ack_file_key) -> str:
    """Obtains the ack file content from the destination bucket."""
    retrieved_object = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=temp_ack_file_key)
    return retrieved_object["Body"].read().decode("utf-8")


def generate_expected_ack_file_row(
    success: bool,
    imms_id: str = MOCK_MESSAGE_DETAILS.imms_id,
    diagnostics: str = None,
    row_id: str = MOCK_MESSAGE_DETAILS.row_id,
    local_id: str = MOCK_MESSAGE_DETAILS.local_id,
    created_at_formatted_string: str = MOCK_MESSAGE_DETAILS.created_at_formatted_string,
):
    """Create an ack row, containing the given message details."""
    if success:
        return (
            f"{row_id}|OK|Information|OK|30001|Business|30001|Success|{created_at_formatted_string}|"
            f"|{local_id}|{imms_id}||True"
        )
    else:
        return (
            f"{row_id}|Fatal Error|Fatal|Fatal Error|30002|Business|30002|Business Level Response Value - "
            f"Processing Error|{created_at_formatted_string}||{local_id}|{imms_id}|{diagnostics}|False"
        )


def generate_sample_existing_ack_content() -> str:
    """Returns sample ack file content with a single success row."""
    return ValidValues.ack_headers + generate_expected_ack_file_row(success=True)


def generate_expected_ack_content(
    incoming_messages: list[dict], existing_content: str = ValidValues.ack_headers
) -> str:
    """Returns the expected_ack_file_content based on the incoming messages"""
    for message in incoming_messages:
        # Determine diagnostics based on the diagnostics value in the incoming message
        diagnostics_dictionary = message.get("diagnostics", {})
        diagnostics = (
            diagnostics_dictionary.get("error_message", "")
            if isinstance(diagnostics_dictionary, dict)
            else "Unable to determine diagnostics issue"
        )

        # Create the ack row based on the incoming message details
        ack_row = generate_expected_ack_file_row(
            success=diagnostics == "",
            row_id=message.get("row_id", MOCK_MESSAGE_DETAILS.row_id),
            created_at_formatted_string=message.get(
                "created_at_formatted_string", MOCK_MESSAGE_DETAILS.created_at_formatted_string
            ),
            local_id=message.get("local_id", MOCK_MESSAGE_DETAILS.local_id),
            imms_id="" if diagnostics else message.get("imms_id", MOCK_MESSAGE_DETAILS.imms_id),
            diagnostics=diagnostics,
        )

        existing_content += ack_row + "\n"

    return existing_content


def validate_ack_file_content(
    incoming_messages: list[dict], existing_file_content: str = ValidValues.ack_headers
) -> None:
    """
    Obtains the ack file content and ensures that it matches the expected content (expected content is based
    on the incoming messages).
    """
    actual_ack_file_content = obtain_current_ack_file_content()
    expected_ack_file_content = generate_expected_ack_content(incoming_messages, existing_file_content)
    assert expected_ack_file_content == actual_ack_file_content
