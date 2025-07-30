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
        logger.info("SAW...5.1 check Patient details")
        if patient:
            logger.info(f"Patient details found for NHS number: {nhs_number}")
            logger.info(f"Patient details: {patient}")
            pds_nhs_number = patient["id"]
            return pds_nhs_number
        else:
            logger.info(f"No patient details found for ID: {nhs_number}")
            return None
    except Exception as e:
        msg = f"Error getting PDS patient details for {nhs_number}"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)
