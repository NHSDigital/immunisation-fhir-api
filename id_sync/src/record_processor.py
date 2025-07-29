'''
    record Processor
'''
from common.clients import logger
from typing import Optional
from pds_details import pds_get_patient_details
from ieds_db_operations import ieds_check_exist, ieds_update_patient_id


def process_record(event_record):

    logger.info("Processing record: %s", event_record)
    body = event_record.get('body', {})
    nhs_number = body.get("subject")
    if nhs_number:
        return process_nhs_number(nhs_number)
    else:
        return {"status": "error", "message": "No NHS number found in event record"}


def process_nhs_number(nhs_number: str) -> Optional[str]:
    # get patient details from PDS
    patient_details = pds_get_patient_details(nhs_number)
    if not patient_details:
        return {"status": "error", "message": f"No records returned for ID: {nhs_number}"}

    patient_details_id = patient_details.get("id")

    base_log_data = {"nhs_number": nhs_number}
    if patient_details_id:
        # if patient NHS != id, update patient index of vax events to new number
        if patient_details_id != nhs_number and patient_details_id:
            if ieds_check_exist(patient_details_id):
                response = ieds_update_patient_id(patient_details_id, nhs_number)
            else:
                response = {"status": "error", "message": f"No records returned for ID: {nhs_number}"}
        else:
            return {"status": "success", "message": "No update required"}
    else:
        response = {"status": "error", "message": f"No patient ID found for NHS number: {nhs_number}"}
    response.update(base_log_data)
    return response
