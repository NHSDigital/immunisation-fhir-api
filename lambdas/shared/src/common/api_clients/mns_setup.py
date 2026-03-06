import logging
import os

import boto3
from botocore.config import Config

from common.api_clients.authentication import AppRestrictedAuth, Service
from common.api_clients.constants import DEV_ENVIRONMENT
from common.api_clients.mns_service import MnsService
from common.api_clients.mock_mns_service import MockMnsService
from common.cache import Cache

logging.basicConfig(level=logging.INFO)
MNS_TEST_QUEUE_URL = os.getenv("MNS_TEST_QUEUE_URL")


def get_mns_service(mns_env: str = "int"):
    if mns_env == DEV_ENVIRONMENT:
        logging.info("Dev environment: Using MockMnsService")
        return MockMnsService(MNS_TEST_QUEUE_URL)
    else:
        boto_config = Config(region_name="eu-west-2")
        cache = Cache(directory="/tmp")  # NOSONAR(S5443)
        logging.info("Creating authenticator...")
        authenticator = AppRestrictedAuth(
            service=Service.PDS,
            secret_manager_client=boto3.client("secretsmanager", config=boto_config),
            environment=mns_env,
            cache=cache,
        )
        logging.info("Authentication Initiated...")
        return MnsService(authenticator)
