import json
from typing import Any, Dict

from common.clients import logger
from ieds_db_operations import (
    extract_patient_resource_from_item,
    get_items_from_patient_id,
    ieds_update_patient_id,
)
from pds_details import pds_get_patient_details, pds_get_patient_id
from utils import make_status


def process_record(event_record: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Processing record with SQS messageId: %s", event_record.get("messageId"))
    body_text = event_record.get("body", "")

    try:
        body = json.loads(body_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse body: %s", body_text)
        return {"status": "error", "message": "Invalid body format"}

    nhs_number = body.get("subject")
    logger.info("Processing MNS event with id: %s", body.get("id"))

    if not nhs_number:
        logger.info("No NHS number found in event record")
        return {"status": "error", "message": "No NHS number found in event record"}

    return process_nhs_number(nhs_number)


def process_nhs_number(nhs_number: str) -> Dict[str, Any]:
    new_nhs_number = pds_get_patient_id(nhs_number)

    if not new_nhs_number:
        return make_status("No patient ID found for NHS number")

    if new_nhs_number == nhs_number:
        return make_status("No update required")

    logger.info("NHS Number has changed. Performing updates on relevant IEDS records")

    try:
        # Fetch PDS Patient resource and IEDS resources for the old NHS number
        pds_patient_resource, ieds_resources = fetch_pds_and_ieds_resources(nhs_number)
    except Exception as e:
        logger.exception("process_nhs_number: failed to fetch demographic details: %s", e)
        return make_status(str(e), status="error")

    logger.info(
        "Fetched IEDS resources. IEDS count: %d",
        len(ieds_resources) if ieds_resources else 0,
    )

    if not ieds_resources:
        logger.info("No IEDS records returned for NHS number")
        return make_status("No records returned for NHS Number")

    # Compare demographics from PDS to each IEDS item, keep only matching records
    matching_records = []
    discarded_count = 0
    for detail in ieds_resources:
        if demographics_match(pds_patient_resource, detail):
            matching_records.append(detail)
        else:
            discarded_count += 1

    if not matching_records:
        logger.info("No records matched PDS demographics: %d", discarded_count)
        return make_status("No records matched PDS demographics; update skipped")

    response = ieds_update_patient_id(nhs_number, new_nhs_number, items_to_update=matching_records)
    # add counts for observability
    response["matched"] = len(matching_records)
    response["discarded"] = discarded_count
    return response


# Function to fetch PDS Patient details and IEDS Immunisation records.
def fetch_pds_and_ieds_resources(nhs_number: str):
    try:
        pds = pds_get_patient_details(nhs_number)
    except Exception as e:
        logger.exception("fetch_pds_and_ieds_resources: failed to fetch PDS details")
        raise RuntimeError("Failed to fetch PDS details") from e

    try:
        ieds = get_items_from_patient_id(nhs_number)
    except Exception as e:
        logger.exception("fetch_pds_and_ieds_resources: failed to fetch IEDS items")
        raise RuntimeError("Failed to fetch IEDS items") from e

    return pds, ieds


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
        pds_name = normalize_strings(extract_normalized_name_from_patient(pds_details))
        pds_gender = normalize_strings(pds_details.get("gender"))
        pds_dob = normalize_strings(pds_details.get("birthDate"))

        # Retrieve patient resource from IEDS item
        patient = extract_patient_resource_from_item(ieds_item)
        if not patient:
            logger.info("demographics_match: no patient resource in IEDS table item")
            return False

        # normalize patient fields from IEDS
        ieds_name = normalize_strings(extract_normalized_name_from_patient(patient))
        ieds_gender = normalize_strings(patient.get("gender"))
        ieds_dob = normalize_strings(patient.get("birthDate"))

        # All required fields must be present
        if not all([pds_name, pds_gender, pds_dob, ieds_name, ieds_gender, ieds_dob]):
            logger.debug("demographics_match: missing required demographics")
            return False

        # Compare fields
        if pds_dob != ieds_dob:
            logger.debug("demographics_match: birthDate mismatch between the patient resources")
            return False

        if pds_gender != ieds_gender:
            logger.debug("demographics_match: gender mismatch between the patient resources")
            return False

        if pds_name != ieds_name:
            logger.debug("demographics_match: name mismatch between the patient resources")
            return False

        return True
    except Exception:
        logger.exception("demographics_match: comparison failed with exception")
        return False
