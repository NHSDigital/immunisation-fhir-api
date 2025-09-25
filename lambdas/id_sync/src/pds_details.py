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
        logger.info(f"get patient details. nhs_number: {nhs_number}")

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
        msg = f"Error getting PDS patient details for {nhs_number}"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)


# Extract Patient identifier value from PDS patient details
def pds_get_patient_id(nhs_number: str) -> str:
    """
    Get PDS patient ID from NHS number.
    :param nhs_number: NHS number of the patient
    :return: PDS patient ID
    """
    try:
        patient_details = pds_get_patient_details(nhs_number)
        if not patient_details:
            return None

        return patient_details["identifier"][0]["value"]

    except Exception as e:
        msg = f"Error getting PDS patient ID for {nhs_number}"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)
