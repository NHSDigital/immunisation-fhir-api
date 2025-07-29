'''
    record Processor
'''
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord
from common.clients import logger
from pds_details import get_pds_patient_details
import json
from typing import Optional
from to_do_code import check_records_exist, update_patient_index


def process_record(event_record: AwsLambdaSqsEventRecord):
    record = AwsLambdaSqsEventRecord(event_record) if isinstance(event_record, dict) else event_record
    logger.info("Processing record: %s", record)

    id = get_id(event_record.body)

    if id:
        # TODO This code is a placeholder for checking if records exist in the database - defaulting to True for now
        exists = check_records_exist(id)

        if exists:
            # get patient details from PDS
            patient_details = get_pds_patient_details(id)
            if not patient_details:
                return {"status": "error", "message": f"No records returned for ID: {id}"}

            patient_details_id = patient_details.get("id")

            # if patient NHS != id, update patient index of vax events to new number
            if patient_details_id != id:
                return update_patient_index(id, patient_details_id)
            else:
                return {"status": "success", "message": "No update required"}
        else:
            return {"status": "error", "message": f"No records found for ID: {id}"}
    else:
        return {"status": "error", "message": "No ID found in event record"}


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
