'''
    record Processor
'''
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord
from common.clients import logger
import json
from typing import Optional

def process_record(event_record: AwsLambdaSqsEventRecord):
    record = AwsLambdaSqsEventRecord(event_record) if isinstance(event_record, dict) else event_record
    logger.info("Processing record: %s", record)

    id = get_id(event_record.body)

    exists = check_records_exist(id)

    return f"hello world {record}"


def get_id(event_body) -> Optional[str]:
    """Extract subject identifier from FHIR Bundle notification event"""
    try:
        # Parse JSON if it's a string
        if isinstance(event_body, str):
            data = json.loads(event_body)
        else:
            data = event_body
        # Navigate through the nested structure
        entries = data.get("entry", [])
        if not entries:
            logger.warning("No entries found in bundle")
            return None

        # Get the first entry's resource
        first_entry = entries[0]
        resource = first_entry.get("resource", {})
        parameters = resource.get("parameter", [])

        # Find the "additional-context" parameter
        for param in parameters:
            if param.get("name") == "additional-context":
                parts = param.get("part", [])

                # Find the "subject" part within additional-context
                for part in parts:
                    if part.get("name") == "subject":
                        value_ref = part.get("valueReference", {})
                        identifier = value_ref.get("identifier", {})
                        subject_id = identifier.get("value")

                        if subject_id:
                            logger.info("Found subject identifier: %s", subject_id)
                            return subject_id

        logger.warning("Subject identifier not found in notification event")
        return None

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.error("Error extracting subject identifier: %s", e)
        return None
