"""
Operations related to PDS (Patient Demographic Service)
"""

import tempfile

from common.authentication import AppRestrictedAuth, Service
from common.cache import Cache
from common.clients import logger, secrets_manager_client
from common.pds_service import PdsService
from exceptions.id_sync_exception import IdSyncException
from os_vars import get_pds_env

pds_env = get_pds_env()
safe_tmp_dir = tempfile.mkdtemp(dir="/tmp")  # NOSONAR


# Get Patient details from external service PDS using NHS number from MNS notification
def pds_get_patient_details(nhs_number: str) -> dict:
    try:
        cache = Cache(directory=safe_tmp_dir)
        authenticator = AppRestrictedAuth(
            service=Service.PDS,
            secret_manager_client=secrets_manager_client,
            environment=pds_env,
            cache=cache,
        )
        pds_service = PdsService(authenticator, pds_env)
        patient = pds_service.get_patient_details(nhs_number)
        return patient
    except Exception as e:
        msg = "Error retrieving patient details from PDS"
        logger.exception(msg)
        raise IdSyncException(message=msg) from e


def get_nhs_number_from_pds_resource(pds_resource: dict) -> str:
    """Simple helper to get the NHS Number from a PDS Resource. No handling as this is a mandatory field in the PDS
    response. Must only use where we have ensured an object has been returned."""
    return pds_resource["identifier"][0]["value"]
