"""Functions for forwarding each row to the Imms API"""

import json
import base64
import logging
from batch_controller import send_request_to_controller
from fhir_controller import make_controller

logging.basicConfig(level="INFO")
logger = logging.getLogger()


def batch_processing_handler(event, context):
    """Forward each row to the Imms FHIR controller"""
    logger.info("Processing started")
    for record in event["Records"]:
        try:
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            send_request_to_controller(make_controller(), message_body)
        except Exception as error:  # pylint:disable=broad-exception-caught
            logger.error("Error processing message: %s", error)
    logger.info("Processing ended")


if __name__ == "__main__":
    batch_processing_handler({"Records": []}, {})
