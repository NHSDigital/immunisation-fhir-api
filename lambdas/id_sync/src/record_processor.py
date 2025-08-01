'''
    record Processor
'''
from common.clients import logger
from typing import Optional
from pds_details import pds_get_patient_id
from ieds_db_operations import ieds_check_exist, ieds_update_patient_id
import json
import ast


def process_record(event_record):

    logger.info("process_record. Processing record: %s", event_record)
    body_text = event_record.get('body', '')
    # convert body to json
    if isinstance(body_text, str):
        try:
            # Try JSON first
            body = json.loads(body_text)
        except json.JSONDecodeError:
            try:
                # Fall back to Python dict syntax
                body = ast.literal_eval(body_text)
            except (ValueError, SyntaxError):
                logger.error("Failed to parse body: %s", body_text)
                return {"status": "error", "message": "Invalid body format"}
    else:
        body = body_text
    nhs_number = body.get("subject")
    logger.info("process record NHS number: %s", nhs_number)
    if nhs_number:
        return process_nhs_number(nhs_number)
    else:
        logger.info("No NHS number found in event record")
        return {"status": "error", "message": "No NHS number found in event record"}


def process_nhs_number(nhs_number: str) -> Optional[str]:
    # get patient details from PDS
    logger.info(f"process_nhs_number. Processing NHS number: {nhs_number}")
    patient_details_id = pds_get_patient_id(nhs_number)

    base_log_data = {"nhs_number": nhs_number}
    if patient_details_id:
        logger.info(f"process_nhs_number. Patient details ID: {patient_details_id}")
        # if patient NHS != id, update patient index of vax events to new number
        if patient_details_id != nhs_number and patient_details_id:
            logger.info(f"process_nhs_number. Update patient ID from {nhs_number} to {patient_details_id}")
            if ieds_check_exist(nhs_number):
                logger.info("process_nhs_number. IEDS record found, updating patient ID")
                response = ieds_update_patient_id(nhs_number, patient_details_id)
            else:
                logger.info("process_nhs_number. No ieds record found for: %s", nhs_number)
                response = {"status": "success", "message": f"No records returned for ID: {nhs_number}"}
        else:
            response = {"status": "success", "message": "No update required"}
    else:
        response = {"status": "success", "message": f"No patient ID found for NHS number: {nhs_number}"}
    response.update(base_log_data)
    return response
