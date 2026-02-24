import logging

import boto3
from botocore.config import Config

from common.api_clients.authentication import AppRestrictedAuth, Service
from common.api_clients.mns_service import MnsService
from common.cache import Cache

logging.basicConfig(level=logging.INFO)


def get_mns_service(mns_env: str = "int"):
    boto_config = Config(region_name="eu-west-2")
    cache = Cache(directory="/tmp")
    logging.info("Creating authenticator...")
    # TODO: MNS and PDS need separate secrets
    authenticator = AppRestrictedAuth(
        service=Service.PDS,
        secret_manager_client=boto3.client("secretsmanager", config=boto_config),
        environment=mns_env,
        cache=cache,
    )

    logging.info("Authentication Initiated...")
    return MnsService(authenticator)
