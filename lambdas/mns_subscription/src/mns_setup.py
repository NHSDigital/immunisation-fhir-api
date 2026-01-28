import logging

import boto3
from botocore.config import Config

from common.authentication import AppRestrictedAuth
from mns_service import MnsService

logging.basicConfig(level=logging.INFO)


def get_mns_service(mns_env: str = "int"):
    boto_config = Config(region_name="eu-west-2")
    authenticator = AppRestrictedAuth(
        secret_manager_client=boto3.client("secretsmanager", config=boto_config),
        environment=mns_env,
    )
    return MnsService(authenticator)
