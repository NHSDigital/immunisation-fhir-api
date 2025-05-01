"""Functions to send a message to SQS"""

import os
from json import dumps as json_dumps
from clients import sqs_client, logger
from errors import InvalidSupplierError, UnhandledSqsError


def send_to_supplier_queue(
    message_body: dict, vaccine_type: str, supplier: str
) -> None:
    """Sends a message to the supplier queue. Raises an exception if the message is not successfully sent."""
    # Check the supplier has been identified (this should already have been validated by initial file validation)
    if not supplier or not vaccine_type:
        error_message = "Message not sent to supplier queue as unable to identify supplier and/ or vaccine type"
        logger.error(error_message)
        raise InvalidSupplierError(error_message)

    try:
        queue_url = os.getenv("QUEUE_URL")
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json_dumps(message_body),
            MessageGroupId=f"{supplier}_{vaccine_type}",
        )
        logger.info("Message sent to SQS queue for supplier: %s", supplier)
    except Exception as error:  # pylint: disable=broad-exception-caught
        error_message = f"An unexpected error occurred whilst sending to SQS: {error}"
        logger.error(error_message)
        raise UnhandledSqsError(error_message) from error


def make_and_send_sqs_message(
    file_key: str,
    message_id: str,
    permission: str,
    vaccine_type: str,
    supplier: str,
    created_at_formatted_string: str,
) -> None:
    """Attempts to send a message to the SQS queue. Raises an exception if the message is not successfully sent."""
    message_body = {
        "message_id": message_id,
        "vaccine_type": vaccine_type,
        "supplier": supplier,
        "filename": file_key,
        "permission": permission,
        "created_at_formatted_string": created_at_formatted_string,
    }

    send_to_supplier_queue(message_body, vaccine_type, supplier)
