import os
import uuid
from datetime import datetime

from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.get_pds_details import pds_get_patient_details
from common.clients import logger
from common.get_service_url import get_service_url
from constants import IMMUNISATION_TYPE, SPEC_VERSION, MnsNotificationPayload
from sqs_dynamo_utils import extract_sqs_imms_data

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")


def create_mns_notification(sqs_event: SQSMessage) -> MnsNotificationPayload:
    """Create a notification payload for MNS."""
    immunisation_url = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)

    # Simple, direct extraction
    imms_data = extract_sqs_imms_data(sqs_event)

    patient_age = calculate_age_at_vaccination(imms_data["person_dob"], imms_data["date_and_time"])

    gp_ods_code = get_practitioner_details_from_pds(imms_data["nhs_number"])

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": immunisation_url,
        "type": IMMUNISATION_TYPE,
        "time": imms_data["date_and_time"],
        "subject": imms_data["nhs_number"],
        "dataref": f"{immunisation_url}/Immunization/{imms_data['imms_id']}",
        "filtering": {
            "generalpractitioner": gp_ods_code,
            "sourceorganisation": imms_data["site_code"],
            "sourceapplication": imms_data["supplier_system"],
            "subjectage": str(patient_age),
            "immunisationtype": imms_data["vaccine_type"],
            "action": imms_data["operation"],
        },
    }


def calculate_age_at_vaccination(birth_date: str, vaccination_date: str) -> int:
    """
    Calculate patient age in years at time of vaccination.
    Expects dates in format: YYYYMMDD or YYYYMMDDThhmmsszz
    """
    birth_date_str = birth_date[:8] if len(birth_date) >= 8 else birth_date
    vacc_date_str = vaccination_date[:8] if len(vaccination_date) >= 8 else vaccination_date

    date_of_birth = datetime.strptime(birth_date_str, "%Y%m%d")
    date_of_vaccination = datetime.strptime(vacc_date_str, "%Y%m%d")

    age_in_year = date_of_vaccination.year - date_of_birth.year
    if (date_of_vaccination.month, date_of_vaccination.day) < (date_of_birth.month, date_of_birth.day):
        age_in_year -= 1

    return age_in_year


def get_practitioner_details_from_pds(nhs_number: str) -> str | None:
    patient_details = pds_get_patient_details(nhs_number)

    general_practitioners = patient_details.get("generalPractitioner", [])
    if not general_practitioners or len(general_practitioners) == 0:
        logger.warning("No GP details found for patient")
        return None

    patient_gp = general_practitioners[0]
    patient_gp_identifier = patient_gp.get("identifier", {})

    gp_ods_code = patient_gp_identifier.get("value")
    if not gp_ods_code:
        logger.warning("GP ODS code not found in practitioner details")
        return None

    # Check if registration is current
    period = patient_gp_identifier.get("period", {})
    gp_period_end_date = period.get("end", None)

    if gp_period_end_date:
        # Parse end date (format: YYYY-MM-DD)
        end_date = datetime.strptime(gp_period_end_date, "%Y-%m-%d").date()
        today = datetime.now().date()

        if end_date < today:
            logger.warning("No current GP registration found for patient")
            return None

    return gp_ods_code
