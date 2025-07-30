'''
    record Processor
'''
import tempfile
from common.clients import logger, secrets_manager_client
from common.cache import Cache
from os_vars import get_pds_env
from common.pds_service import PdsService
from common.authentication import AppRestrictedAuth, Service
from models.id_sync_exception import IdSyncException

pds_env = get_pds_env()
safe_tmp_dir = tempfile.mkdtemp(dir="/tmp")  # NOSONAR


def pds_get_patient_details(nhs_number: str) -> dict:
    try:
        logger.info(f"pds_get_patient_details. nhs_number: {nhs_number}")

        logger.info("SAW...1")
        cache = Cache(directory=safe_tmp_dir)
        logger.info("SAW...2")
        authenticator = AppRestrictedAuth(
            service=Service.PDS,
            secret_manager_client=secrets_manager_client,
            environment=pds_env,
            cache=cache,
        )
        logger.info("SAW...3")
        pds_service = PdsService(authenticator, pds_env)
        logger.info("SAW...4")
        patient = pds_service.get_patient_details(nhs_number)
        logger.info("SAW...5")
        return patient
    except Exception as e:
        msg = f"Error getting PDS patient details for {nhs_number}"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)


def pds_get_patient_id(nhs_number: str) -> str:
    """
    Get PDS patient ID from NHS number.
    :param nhs_number: NHS number of the patient
    :return: PDS patient ID
    """
    try:
        logger.info(f"get_pds_patient_id. nhs_number: {nhs_number}")
        patient_details = pds_get_patient_details(nhs_number)
        if not patient_details:
            return None

        return patient_details["identifier"][0]["value"]

    # ✅ Remove the IdSyncException catch since you're just re-raising
    except Exception as e:
        msg = f"Error getting PDS patient ID for {nhs_number}"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)
