"""
Operations related to PDS (Patient Demographic Service)
"""

import os
import tempfile

from common.api_clients.authentication import AppRestrictedAuth, Service
from common.api_clients.errors import PdsSyncException
from common.api_clients.pds_service import PdsService
from common.cache import Cache
from common.clients import get_secrets_manager_client, logger

PDS_ENV = os.getenv("PDS_ENV", "int")
safe_tmp_dir = tempfile.mkdtemp(dir="/tmp")  # NOSONAR(S5443)


# Get Patient details from external service PDS using NHS number from MNS notification
def pds_get_patient_details(nhs_number: str) -> dict:
    try:
        cache = Cache(directory=safe_tmp_dir)
        authenticator = AppRestrictedAuth(
            service=Service.PDS,
            secret_manager_client=get_secrets_manager_client(),
            environment=PDS_ENV,
            cache=cache,
        )
        pds_service = PdsService(authenticator, PDS_ENV)
        patient = pds_service.get_patient_details(nhs_number)
        return patient
    except Exception as e:
        msg = "Error retrieving patient details from PDS"
        logger.exception(msg)
        raise PdsSyncException(message=msg) from e
