from authentication import AppRestrictedAuth
import logging
from cache import Cache
from mns_service import MnsService
import boto3
from authentication import AppRestrictedAuth, Service
from botocore.config import Config

logging.basicConfig(level=logging.INFO)


def run_subscription():
    try:
        mns_env: str = "int"

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
        mns = MnsService(authenticator)

        logging.info("Subscribing to MNS...")
        result = mns.subscribe_notification()
        logging.info(f"Subscription Result: {result}")
        return result
    except Exception:
        logging.exception("Failed to complete MNS subscription process")
        raise


if __name__ == "__main__":
    result = run_subscription()
    print("Subscription Result:", result)
