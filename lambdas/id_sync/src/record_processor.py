'''
    record Processor
'''
from common.clients import logger
import json
from typing import Optional
from nhs_number_processor import process_nhs_number


def process_record(event_record):

    logger.info("Processing record: %s", event_record)
    body = event_record.get('body', {})
    nhs_number = get_id(body)
    if nhs_number:
        return process_nhs_number(nhs_number)
    else:
        return {"status": "error", "message": "No NHS number found in event record"}


def get_id(event_body) -> Optional[str]:
    """Extract subject identifier from FHIR Bundle notification event"""
    try:
        # Parse JSON if it's a string
        if isinstance(event_body, str):
            data = json.loads(event_body)
        else:
            data = event_body
        # Navigate through the nested structure
        subject = data.get("subject")
        return subject

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.error("Error extracting subject identifier: %s", e)
        return None
