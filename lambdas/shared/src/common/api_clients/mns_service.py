import json
import logging
import os
import uuid

import requests

from common.api_clients.authentication import AppRestrictedAuth
from common.api_clients.errors import raise_error_response
from common.api_clients.retry import request_with_retry_backoff

SQS_ARN = os.getenv("SQS_ARN")

apigee_env = os.getenv("APIGEE_ENVIRONMENT", "int")
MNS_URL = (
    "https://api.service.nhs.uk/multicast-notification-service"
    if apigee_env == "prod"
    else "https://int.api.service.nhs.uk/multicast-notification-service"
)


class MnsService:
    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        self.access_token = self.authenticator.get_access_token()
        self.request_headers = {
            "Content-Type": "application/fhir+json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Correlation-ID": str(uuid.uuid4()),
        }
        self.subscription_payload = {
            "resourceType": "Subscription",
            "status": "requested",
            "reason": "Subscribe SQS to NHS Number Change Events",
            "criteria": "eventType=nhs-number-change-2",
            "channel": {
                "type": "message",
                "endpoint": SQS_ARN,
                "payload": "application/json",
            },
        }

        logging.info(f"Using SQS ARN for subscription: {SQS_ARN}")

    def subscribe_notification(self) -> dict | None:
        response = requests.request(
            "POST",
            f"{MNS_URL}/subscriptions",
            headers=self.request_headers,
            timeout=15,
            data=json.dumps(self.subscription_payload),
        )
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise_error_response(response)

    def get_subscription(self) -> dict | None:
        response = request_with_retry_backoff(
            "GET", f"{MNS_URL}/subscriptions", headers=self.request_headers, timeout=10
        )
        logging.info(f"GET {MNS_URL}/subscriptions")
        logging.debug(f"Headers: {self.request_headers}")

        if response.status_code == 200:
            bundle = response.json()
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", entry)
                print(f"get resource sub: {resource}")
                logging.debug(f"get resource sub: {resource}")
                channel = resource.get("channel", {})
                if channel.get("endpoint") == SQS_ARN:
                    return resource
            return None
        else:
            raise_error_response(response)

    def check_subscription(self) -> dict:
        """
        Ensures that a subscription exists for this SQS_ARN.
        If not found, creates one.
        Returns the subscription.
        """
        try:
            existing = self.get_subscription()
            if existing:
                logging.info("Subscription for this SQS ARN already exists.")
                return existing
            else:
                logging.info("No subscription found for this SQS ARN. Creating new subscription...")
                return self.subscribe_notification()
        except Exception as e:
            logging.error(f"Error ensuring subscription: {e}")
            raise

    def delete_subscription(self, subscription_id: str) -> str:
        """Delete the subscription by ID."""
        url = f"{MNS_URL}/subscriptions/{subscription_id}"
        response = request_with_retry_backoff("DELETE", url, headers=self.request_headers, timeout=10)
        if response.status_code == 204:
            logging.info(f"Deleted subscription {subscription_id}")
            return "Subscription Successfully Deleted..."
        else:
            raise_error_response(response)

    def check_delete_subscription(self):
        try:
            resource = self.get_subscription()
            if not resource:
                return "No matching subscription found to delete."

            subscription_id = resource.get("id")
            if not subscription_id:
                return "Subscription resource missing 'id' field."

            self.delete_subscription(subscription_id)
            return "Subscription successfully deleted"
        except Exception as e:
            return f"Error deleting subscription: {str(e)}"

    def publish_notification(self, notification_payload) -> dict | None:
        self.request_headers["Content-Type"] = "application/cloudevents+json"
        response = requests.request(
            "POST", f"{MNS_URL}/events", headers=self.request_headers, timeout=15, data=json.dumps(notification_payload)
        )
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise_error_response(response)
