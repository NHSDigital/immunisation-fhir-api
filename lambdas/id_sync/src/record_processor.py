from common.clients import logger
from typing import Dict, Any
from pds_details import pds_get_patient_id, pds_get_patient_details, normalize_name_from_pds
from ieds_db_operations import (
    ieds_check_exist,
    ieds_update_patient_id,
    extract_patient_resource_from_item,
    get_items_from_patient_id,
)
import json
import ast


def process_record(event_record: Dict[str, Any]) -> Dict[str, Any]:

    logger.info("process_record. Processing record: %s", event_record)
    body_text = event_record.get('body', '')

    # convert body to json (try JSON first, then fall back to Python literal)
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
        return process_nhs_number(nhs_number)

    logger.info("No NHS number found in event record")
    return {"status": "error", "message": "No NHS number found in event record"}


def process_nhs_number(nhs_number: str) -> Dict[str, Any]:
    # get patient details from PDS
    new_nhs_number = pds_get_patient_id(nhs_number)

    if not new_nhs_number:
        return {
            "status": "success",
            "message": "No patient ID found for NHS number",
            "nhs_number": nhs_number,
        }

    if new_nhs_number == nhs_number:
        return {
            "status": "success",
            "message": "No update required",
            "nhs_number": nhs_number,
        }
    logger.info("Update patient ID from %s to %s", nhs_number, new_nhs_number)

    if ieds_check_exist(nhs_number):
        # Fetch PDS details for demographic comparison
        try:
            pds_details = pds_get_patient_details(nhs_number)
        except Exception:
            logger.exception("process_nhs_number: failed to fetch PDS details, aborting update")
            return {
                "status": "error",
                "message": "Failed to fetch PDS details for demographic comparison",
                "nhs_number": nhs_number,
            }

        # Get IEDS items for this patient id and compare demographics
        try:
            items = get_items_from_patient_id(nhs_number)
        except Exception:
            logger.exception("process_nhs_number: failed to fetch IEDS items, aborting update")
            return {
                "status": "error",
                "message": "Failed to fetch IEDS items for demographic comparison",
                "nhs_number": nhs_number,
            }

        # If at least one IEDS item matches demographics, proceed with update
        match_found = False
        for item in items:
            try:
                if demographics_match(pds_details, item):
                    match_found = True
                    break
            except Exception:
                logger.exception("process_nhs_number: error while comparing demographics for item: %s", item)

        if not match_found:
            logger.info("process_nhs_number: No IEDS items matched PDS demographics. Skipping update for %s", nhs_number)
            response = {
                "status": "success",
                "message": "No IEDS items matched PDS demographics; update skipped",
            }
        else:
            response = ieds_update_patient_id(nhs_number, new_nhs_number)
    else:
        logger.info("No IEDS record found for: %s", nhs_number)
        response = {"status": "success", "message": f"No records returned for ID: {nhs_number}"}

    response["nhs_number"] = nhs_number
    return response

def extract_normalized_name_from_patient(patient: dict) -> str | None:
    """Return a normalized 'given family' name string from a Patient resource or None."""
    if not patient:
        return None
    name = patient.get("name")
    if not name:
        return None
    try:
        name_entry = name[0] if isinstance(name, list) else name
        given = name_entry.get("given")
        given_str = None
        if isinstance(given, list) and given:
            given_str = given[0]
        elif isinstance(given, str):
            given_str = given
        family = name_entry.get("family")
        parts = [p for p in [given_str, family] if p]
        return " ".join(parts).strip().lower() if parts else None
    except Exception:
        return None


def demographics_match(pds_details: dict, ieds_item: dict) -> bool:
    """Compare PDS patient details from PDS to an IEDS item (FHIR Patient resource).
    Returns True if name, birthDate and gender match (when present in both sources).
    If required fields are missing or unparsable on the IEDS side the function returns False.
    """
    try:
         
        def normalize_strings(item: Any) -> str | None:
            return str(item).strip().lower() if item else None
        
        # Retrieve patient resource from PDS
        pds_name = normalize_strings(normalize_name_from_pds(pds_details))
        pds_gender = normalize_strings(pds_details.get("gender"))
        pds_birth = normalize_strings(pds_details.get("birthDate"))

        # Retrieve patient resource from IEDS item
        patient = extract_patient_resource_from_item(ieds_item)
        if not patient:
            logger.debug("demographics_match: no patient resource in IEDS table item")
            return False

        # normalize patient name
        ieds_name = extract_normalized_name_from_patient(patient)

        ieds_gender = normalize_strings(patient.get("gender"))
        ieds_birth = patient.get("birthDate")

        if pds_birth and ieds_birth and pds_birth != ieds_birth:
            logger.debug("demographics_match: birthDate mismatch %s != %s", pds_birth, ieds_birth)
            return False

        if pds_gender and ieds_gender and pds_gender != ieds_gender:
            logger.debug("demographics_match: gender mismatch %s != %s", pds_gender, ieds_gender)
            return False

        if pds_name and ieds_name and pds_name != ieds_name:
            logger.debug("demographics_match: name mismatch %s != %s", pds_name, ieds_name)
            return False

        return True
    except Exception:
        logger.exception("demographics_match: comparison failed with exception")
        return False