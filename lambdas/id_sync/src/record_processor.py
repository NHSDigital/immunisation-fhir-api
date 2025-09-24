from common.clients import logger
from typing import Dict, Any
from pds_details import pds_get_patient_id, pds_get_patient_details
from ieds_db_operations import (
    ieds_update_patient_id,
    extract_patient_resource_from_item,
    get_items_from_patient_id,
)
from utils import make_status
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
    # Reached
    logger.info("process record NHS number: %s", nhs_number)
    if nhs_number:
        return process_nhs_number(nhs_number)

    logger.info("No NHS number found in event record")
    return {"status": "error", "message": "No NHS number found in event record"}


def process_nhs_number(nhs_number: str) -> Dict[str, Any]:
    # get patient details from PDS
    new_nhs_number = pds_get_patient_id(nhs_number)

    if not new_nhs_number:
        return make_status("No patient ID found for NHS number", nhs_number)

    if new_nhs_number == nhs_number:
        return make_status("No update required", nhs_number)

    logger.info("Update patient ID from %s to %s", nhs_number, new_nhs_number)

    try:
        # Fetch PDS Patient resource and IEDS resources for the old NHS number
        pds_patient_resource, ieds_resources = fetch_pds_and_ieds_resources(nhs_number)
    except Exception as e:
        logger.exception("process_nhs_number: failed to fetch demographic details: %s", e)
        return make_status(str(e), nhs_number, "error")

    logger.info("Fetched PDS details: %s", pds_patient_resource)
    logger.info("Fetched IEDS resources. IEDS count: %d", len(ieds_resources), ieds_resources if ieds_resources else 0)

    if not ieds_resources:
        logger.info("No IEDS records returned for NHS number: %s", nhs_number)
        return make_status(f"No records returned for ID: {nhs_number}", nhs_number)

    # Compare demographics from PDS to each IEDS item, keep only matching records
    matching_records = []
    discarded_count = 0
    discarded_records = []
    for detail in ieds_resources:
        if demographics_match(pds_patient_resource, detail):
            matching_records.append(detail)
        else:
            discarded_count += 1
            discarded_records.append(detail)

    if not matching_records:
        logger.info("No records matched PDS demographics: %d", discarded_count)
        return make_status("No records matched PDS demographics; update skipped", nhs_number)

    response = ieds_update_patient_id(
        nhs_number, new_nhs_number, items_to_update=matching_records
    )
    response["nhs_number"] = nhs_number
    # add counts for observability
    response["matched"] = len(matching_records)
    response["discarded"] = discarded_count
    return response


# Function to fetch PDS Patient details and IEDS Immunisation records
def fetch_pds_and_ieds_resources(nhs_number: str):
    logger.info("fetch_pds_and_ieds_resources: fetching for %s", nhs_number)
    try:
        pds = pds_get_patient_details(nhs_number)
        logger.info("fetch_pds_resources: fetching for %s", pds)
    except Exception as e:
        logger.exception("fetch_pds_and_ieds_resources: failed to fetch PDS details for %s", nhs_number)
        raise RuntimeError("Failed to fetch PDS details") from e

    try:
        ieds = get_items_from_patient_id(nhs_number)
    except Exception as e:
        logger.exception("fetch_pds_and_ieds_resources: failed to fetch IEDS items for %s", nhs_number)
        raise RuntimeError("Failed to fetch IEDS items") from e

    count = len(ieds)
    logger.info("fetch_pds_and_ieds_resources: fetched PDS and %d IEDS items for %s", count, nhs_number)
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
        pds_birth = normalize_strings(pds_details.get("birthDate"))
        logger.info("demographics_match: demographics match for %s", pds_name, pds_gender, pds_birth)

        # Retrieve patient resource from IEDS item
        patient = extract_patient_resource_from_item(ieds_item)
        if not patient:
            logger.info("demographics_match: no patient resource in IEDS table item")
            return False

        # normalize patient fields from IEDS
        ieds_name = normalize_strings(extract_normalized_name_from_patient(patient))
        ieds_gender = normalize_strings(patient.get("gender"))
        ieds_birth = normalize_strings(patient.get("birthDate"))
        logger.info("demographics_match: demographics match for %s", patient)

        # All required fields must be present
        if not all([pds_name, pds_gender, pds_birth, ieds_name, ieds_gender, ieds_birth]):
            logger.info("demographics_match: missing required demographics")
            return False

        # Compare fields
        if pds_birth != ieds_birth:
            logger.info("demographics_match: birthDate mismatch %s != %s", pds_birth, ieds_birth)
            return False

        if pds_gender != ieds_gender:
            logger.info("demographics_match: gender mismatch %s != %s", pds_gender, ieds_gender)
            return False

        if pds_name != ieds_name:
            logger.info("demographics_match: name mismatch %s != %s", pds_name, ieds_name)
            return False

        logger.info("demographics_match: demographics match for %s", patient)
        return True
    except Exception:
        logger.exception("demographics_match: comparison failed with exception")
        return False
