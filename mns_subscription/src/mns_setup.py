import logging
from cache import Cache
from mns_service import MnsService
import boto3
from authentication import AppRestrictedAuth, Service
from botocore.config import Config

logging.basicConfig(level=logging.INFO)


def get_mns_service(mns_env: str = "int"):
    boto_config = Config(region_name="eu-west-2")
    cache = Cache(directory="/tmp")
    logging.info("Creating authenticator...")
    authenticator = AppRestrictedAuth(
        service=Service.MNS,
        secret_manager_client=boto3.client("secretsmanager", config=boto_config),
        environment=mns_env,
        cache=cache,
    )

    logging.info("Creating MNS service...")
    return MnsService(authenticator)
