'''
    nhs number Processor
'''
from common.clients import logger
from pds_details import get_pds_patient_details
from typing import Optional
from ieds_db_operations import check_record_exist_in_IEDS, update_patient_id_in_IEDS


def process_nhs_number(nhs_number: str) -> Optional[str]:
    # get patient details from PDS
    patient_details = get_pds_patient_details(nhs_number)
    if not patient_details:
        return {"status": "error", "message": f"No records returned for ID: {nhs_number}"}

    patient_details_id = patient_details.get("id")

    # if patient NHS != id, update patient index of vax events to new number
    if patient_details_id != nhs_number:
        if check_record_exist_in_IEDS(patient_details_id):
            logger.info("Updating patient ID from %s to %s", id, patient_details_id)
            return update_patient_id_in_IEDS(nhs_number, patient_details_id)
        else:
            return {"status": "error", "message": f"No records returned for ID: {nhs_number}"}
    else:
        return {"status": "success", "message": "No update required"}
