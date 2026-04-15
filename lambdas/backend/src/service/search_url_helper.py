"""Module containing helper functions for the constructions of Immunisation FHIR API search URLs"""

import datetime
import urllib.parse

from common.get_service_url import get_service_url
from controller.constants import (
    IMMUNIZATION_TARGET_LEGACY_KEY_NAME,
    ImmunizationSearchParameterName,
)
from controller.parameter_parser import PATIENT_IDENTIFIER_SYSTEM


def create_url_for_bundle_link(
    immunization_targets: set[str],
    patient_nhs_number: str,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    include: str | None,
    service_env: str | None,
    service_base_path: str | None,
    target_disease_codes_for_url: set[str] | None = None,
) -> str:
    """Creates url for the searchset Bundle Link. When target_disease_codes_for_url is provided, uses target-disease
    param instead of vaccination type params."""
    if target_disease_codes_for_url:
        params = {
            ImmunizationSearchParameterName.TARGET_DISEASE: ",".join(sorted(target_disease_codes_for_url)),
            ImmunizationSearchParameterName.PATIENT_IDENTIFIER: f"{PATIENT_IDENTIFIER_SYSTEM}|{patient_nhs_number}",
        }
    else:
        params = {
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
