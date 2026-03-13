"""
Operations related to PDS (Patient Demographic Service)
"""

import os

from common.api_clients.authentication import AppRestrictedAuth
from common.api_clients.errors import PdsSyncException
from common.api_clients.pds_service import PdsService
from common.clients import get_secrets_manager_client, logger

PDS_ENV = os.getenv("PDS_ENV", "int")

_pds_service: PdsService | None = None


def get_pds_service() -> PdsService:
    global _pds_service
    if _pds_service is None:
        authenticator = AppRestrictedAuth(
            secret_manager_client=get_secrets_manager_client(),
            environment=PDS_ENV,
        )
        _pds_service = PdsService(authenticator, PDS_ENV)

    return _pds_service


# Get Patient details from external service PDS using NHS number from MNS notification
def pds_get_patient_details(nhs_number: str) -> dict:
    try:
        patient = get_pds_service().get_patient_details(nhs_number)
        return patient
    except Exception as e:
        msg = "Error retrieving patient details from PDS"
        logger.exception(msg)
        raise PdsSyncException(message=msg) from e
