from common.clients import logger
from typing import Dict, Any
from pds_details import pds_get_patient_id
from ieds_db_operations import ieds_check_exist, ieds_update_patient_id
import json
import ast


def process_record(event_record) -> Dict[str, Any]:

    logger.info("process_record. Processing record: %s", event_record)
    body_text = event_record.get('body', '')
    if isinstance(body_text, str):
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            try:
                body = ast.literal_eval(body_text)
            except (ValueError, SyntaxError):
                logger.error("Failed to parse body: %s", body_text)
                return {"status": "error", "message": "Invalid body format"}
    else:
        body = body_text
    nhs_number = body.get("subject")
    logger.info("process record NHS number: %s", nhs_number)
    if nhs_number:
        if not _is_valid_nhs(nhs_number):
            logger.error("Invalid NHS number format: %s", nhs_number)
            return {"status": "error", "message": "Invalid NHS number format", "nhs_number": nhs_number}
        return process_nhs_number(nhs_number)
    else:
        logger.info("No NHS number found in event record")
        return {"status": "error", "message": "No NHS number found in event record"}


def process_nhs_number(nhs_number: str) -> Dict[str, Any]:
    # get patient details from PDS
    new_nhs_number = pds_get_patient_id(nhs_number)

    base_log_data = {"nhs_number": nhs_number}
    if new_nhs_number:
        if new_nhs_number != nhs_number:
            logger.info("process_nhs_number. Update patient ID from %s to %s", nhs_number, new_nhs_number)
            if ieds_check_exist(nhs_number):
                response = ieds_update_patient_id(nhs_number, new_nhs_number)
            else:
                logger.info("process_nhs_number. No ieds record found for: %s", nhs_number)
                response = {"status": "success", "message": f"No records returned for ID: {nhs_number}"}
        else:
            response = {"status": "success", "message": "No update required"}
    else:
        response = {"status": "success", "message": f"No patient ID found for NHS number: {nhs_number}"}
    response.update(base_log_data)
    return response


def _is_valid_nhs(nhs: str) -> bool:
    """Basic validation: NHS number must be 10 digits. (Optional: add MOD11 check later)"""
    return isinstance(nhs, str) and nhs.isdigit() and len(nhs) == 10
