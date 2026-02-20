"""Module containing helper functions for the constructions of Immunisation FHIR API search URLs"""

import datetime
import urllib.parse
from typing import Optional

from common.get_service_url import get_service_url
from controller.constants import IMMUNIZATION_TARGET_LEGACY_KEY_NAME, ImmunizationSearchParameterName
from controller.parameter_parser import PATIENT_IDENTIFIER_SYSTEM


def create_url_for_bundle_link(
    immunization_targets: set[str],
    patient_nhs_number: str,
    date_from: Optional[datetime.date],
    date_to: Optional[datetime.date],
    include: Optional[str],
    service_env: Optional[str],
    service_base_path: Optional[str],
) -> str:
    """Creates url for the searchset Bundle Link."""
    params = {
        # Temporarily maintaining this for backwards compatibility with imms history, but we should remove it
        IMMUNIZATION_TARGET_LEGACY_KEY_NAME: ",".join(immunization_targets),
        ImmunizationSearchParameterName.IMMUNIZATION_TARGET: ",".join(immunization_targets),
        ImmunizationSearchParameterName.PATIENT_IDENTIFIER: f"{PATIENT_IDENTIFIER_SYSTEM}|{patient_nhs_number}",
    }

    if date_from:
        params[ImmunizationSearchParameterName.DATE_FROM] = date_from.isoformat()
    if date_to:
        params[ImmunizationSearchParameterName.DATE_TO] = date_to.isoformat()
    if include:
        params[ImmunizationSearchParameterName.INCLUDE] = include

    query = urllib.parse.urlencode(params)
    return f"{get_service_url(service_env, service_base_path)}/Immunization?{query}"
