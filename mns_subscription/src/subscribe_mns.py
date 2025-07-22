from authentication import AppRestrictedAuth
import os
from cache import Cache
from mns_service import MnsService
import boto3
from authentication import Service
from botocore.config import Config


def run_subscription():
    mns_env: str = os.getenv("MNS_ENV", "int")

    boto_config = Config(region_name="eu-west-2")
    cache = Cache(directory="/tmp")
    authenticator = AppRestrictedAuth(
        service=Service.MNS,
        secret_manager_client=boto3.client("secretsmanager", config=boto_config),
        environment=mns_env,
        cache=cache,
    )
    mns = MnsService(authenticator, mns_env)
    return mns.subscribeNotification()


if __name__ == "__main__":
    result = run_subscription()
    print("Subscription Result:", result)
