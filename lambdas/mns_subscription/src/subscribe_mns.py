import logging
import os

from common.api_clients.mns_setup import get_mns_service

apigee_env = os.getenv("APIGEE_ENVIRONMENT", "int")


def run_subscription_for_pds_event():
    mns = get_mns_service(mns_env=apigee_env)
    return mns.check_subscription()


def run_subscription_for_imms_event(event_type: str):
    mns = get_mns_service(mns_env=apigee_env)
    return mns.subscribe_to_event(event_type)


def run_subscription():
    # Subscribe to PDS events (NHS number change)
    pds_subscription_result = run_subscription_for_pds_event()
    logging.info(f"PDS Subscription Result: {pds_subscription_result}")

    # Subscribe to immunization events
    imms_subscription_result = run_subscription_for_imms_event("imms-vaccination-record-change-1")
    logging.info(f"Immunization Subscription Result: {imms_subscription_result}")

    return {
        "pds_subscription": pds_subscription_result,
        "imms_subscription": imms_subscription_result,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_subscription()
    logging.info(f"Subscription Result: {result}")
