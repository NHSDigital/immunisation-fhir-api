import logging
import os

from mns_setup import get_mns_service

apigee_env = os.getenv("APIGEE_ENVIRONMENT", "int")


def run_subscription():
    mns = get_mns_service(mns_env=apigee_env)
    return mns.check_subscription()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_subscription()
    logging.info(f"Subscription Result: {result}")
