'''
    record Processor
'''
from common.clients import logger, secrets_manager_client
from common.cache import Cache
from clients import pds_env
from common.pds_service import PdsService
from common.authentication import AppRestrictedAuth, Service


def get_pds_patient_details(nhs_number: str) -> dict:
    try:
        logger.info(f"Get PDS patient details for {nhs_number}")

        cache = Cache("tmp")
        authenticator = AppRestrictedAuth(
            service=Service.PDS,
            secret_manager_client=secrets_manager_client,
            environment=pds_env,
            cache=cache,
        )
        pds_service = PdsService(authenticator, pds_env)

        patient = pds_service.get_patient_details(nhs_number)

        if patient:
            pds_nhs_number = patient["identifier"][0]["value"]
            return pds_nhs_number
        else:
            logger.info(f"No patient details found for ID: {nhs_number}")
            return None
    except Exception:
        logger.exception(f"Error getting PDS patient details for {nhs_number}")
        return None
