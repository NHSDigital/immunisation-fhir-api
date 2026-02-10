"""Utils functions for the ack backend tests"""

import json
from copy import deepcopy
from typing import Optional

from boto3 import client as boto3_client

from tests.utils.mock_environment_variables import AUDIT_TABLE_NAME, REGION_NAME, BucketNames
from tests.utils.values_for_ack_backend_tests import MOCK_MESSAGE_DETAILS, ValidValues

firehose_client = boto3_client("firehose", region_name=REGION_NAME)


def add_audit_entry_to_table(dynamodb_client, batch_event_message_id: str, record_count: Optional[int] = None) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {"status": {"S": "Preprocessed"}, "message_id": {"S": batch_event_message_id}}

    if record_count is not None:
        audit_table_entry["record_count"] = {"N": str(record_count)}

    dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_table_entry)


def generate_event(test_messages: list[dict], include_eof_message: bool = False) -> dict:
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

    if include_eof_message:
        incoming_message_body.append(MOCK_MESSAGE_DETAILS.eof_message)

    return {"Records": [{"body": json.dumps(incoming_message_body)}]}


def setup_existing_ack_file(file_key, file_content, s3_client):
    """Uploads an existing file with the given content."""
    s3_client.put_object(Bucket=BucketNames.DESTINATION, Key=file_key, Body=file_content)


def obtain_current_ack_file_content(s3_client, temp_ack_file_key: str = MOCK_MESSAGE_DETAILS.temp_ack_file_key) -> dict:
    """Obtains the ack file content from the destination bucket."""
    retrieved_object = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=temp_ack_file_key)
    return json.loads(retrieved_object["Body"].read().decode("utf-8"))


def obtain_completed_ack_file_content(
    s3_client, complete_ack_file_key: str = MOCK_MESSAGE_DETAILS.archive_ack_file_key
) -> dict:
    """Obtains the ack file content from the forwardedFile directory"""
    retrieved_object = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=complete_ack_file_key)
    return json.loads(retrieved_object["Body"].read().decode("utf-8"))


def generate_expected_ack_file_element(
    success: bool,
    imms_id: str = MOCK_MESSAGE_DETAILS.imms_id,
    diagnostics: str = None,
    row_id: str = MOCK_MESSAGE_DETAILS.row_id,
    local_id: str = MOCK_MESSAGE_DETAILS.local_id,
    created_at_formatted_string: str = MOCK_MESSAGE_DETAILS.created_at_formatted_string,
) -> dict:
    """Create an ack element, containing the given message details."""
    if success:
        return None  # we no longer process success elements
    else:
        return {
            "rowId": int(row_id.split("^")[-1]),
            "responseCode": "30002",
            "responseDisplay": "Business Level Response Value - Processing Error",
            "severity": "Fatal",
            "localId": local_id,
            "operationOutcome": "" if not diagnostics else diagnostics,
        }


def generate_sample_existing_ack_content(message_id: str = "test_file_id") -> dict:
    """Returns sample ack file content with a single failure row."""
    sample_content = deepcopy(ValidValues.ack_initial_content)
    sample_content["messageHeaderId"] = message_id
    sample_content["failures"].append(generate_expected_ack_file_element(success=False))
    return sample_content


def generate_expected_ack_content(
    incoming_messages: list[dict], existing_content: str = ValidValues.ack_initial_content
) -> dict:
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
        ack_element = generate_expected_ack_file_element(
            success=diagnostics == "",
            row_id=message.get("row_id", MOCK_MESSAGE_DETAILS.row_id),
            created_at_formatted_string=message.get(
                "created_at_formatted_string",
                MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ),
            local_id=message.get("local_id", MOCK_MESSAGE_DETAILS.local_id),
            imms_id=("" if diagnostics else message.get("imms_id", MOCK_MESSAGE_DETAILS.imms_id)),
            diagnostics=diagnostics,
        )

        existing_content["failures"].append(ack_element)

    return existing_content


def validate_ack_file_content(
    s3_client,
    incoming_messages: list[dict],
    existing_file_content: str = ValidValues.ack_initial_content,
    is_complete: bool = False,
) -> None:
    """
    Obtains the ack file content and ensures that it matches the expected content (expected content is based
    on the incoming messages).
    """
    actual_ack_file_content = (
        obtain_current_ack_file_content(s3_client, MOCK_MESSAGE_DETAILS.temp_ack_file_key)
        if not is_complete
        else obtain_completed_ack_file_content(s3_client, MOCK_MESSAGE_DETAILS.archive_ack_file_key)
    )
    existing_file_content_copy = deepcopy(existing_file_content)
    expected_ack_file_content = generate_expected_ack_content(incoming_messages, existing_file_content_copy)

    # NB: disregard real-time generated fields
    actual_ack_file_content["generatedDate"] = expected_ack_file_content["generatedDate"]
    actual_ack_file_content["summary"]["ingestionTime"] = expected_ack_file_content["summary"]["ingestionTime"]

    assert expected_ack_file_content == actual_ack_file_content
