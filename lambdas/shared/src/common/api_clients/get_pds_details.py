"""
Operations related to PDS (Patient Demographic Service)
"""

import os

from common.api_clients.authentication import AppRestrictedAuth
from common.api_clients.errors import PdsSyncException
from common.api_clients.pds_service import PdsService
from common.clients import get_secrets_manager_client, logger

_pds_service: PdsService | None = None
_pds_service_config: tuple[str, str | None] | None = None


def get_pds_service() -> PdsService:
    global _pds_service, _pds_service_config
    environment = os.getenv("PDS_ENV", "int")
    base_url = os.getenv("PDS_BASE_URL", "").strip() or None
    config = (environment, base_url)

    if _pds_service is None or _pds_service_config != config:
        authenticator = (
            None
            if base_url
            else AppRestrictedAuth(secret_manager_client=get_secrets_manager_client(), environment=environment)
        )
        _pds_service = PdsService(authenticator, environment, base_url=base_url)
        _pds_service_config = config
    return _pds_service


# Get Patient details from external service PDS using NHS number from MNS notification
def pds_get_patient_details(nhs_number: str) -> dict:
    try:
        return get_pds_service().get_patient_details(nhs_number)
    except Exception as e:
        msg = "Error retrieving patient details from PDS"
        logger.exception(msg)
        raise PdsSyncException(message=msg) from e
