import requests
import os
import uuid
import logging
import json
from authentication import AppRestrictedAuth
from models.errors import (
    UnhandledResponseError,
    ResourceFoundError,
    UnauthorizedError,
    ServerError,
    TokenValidationError
)

SQS_ARN = os.getenv("SQS_ARN")
MNS_URL = "https://int.api.service.nhs.uk/multicast-notification-service/subscriptions"


class MnsService:
    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        self.access_token = self.authenticator.get_access_token()
        self.request_headers = {
            'Content-Type': 'application/fhir+json',
            'Authorization': f'Bearer {self.access_token}',
            'X-Correlation-ID': str(uuid.uuid4())
        }
        self.subscription_payload = {
            "resourceType": "Subscription",
            "status": "requested",
            "reason": "Subscribe SQS to NHS Number Change Events",
            "criteria": "eventType=nhs-number-change-2",
            "channel": {
                "type": "message",
                "endpoint": SQS_ARN,
                "payload": "application/json"
                }
            }

        logging.info(f"Using SQS ARN for subscription: {SQS_ARN}")

    def subscribe_notification(self) -> dict | None:

        response = requests.post(MNS_URL, headers=self.request_headers, data=json.dumps(self.subscription_payload))

        print(f"Access Token: {self.access_token}")
        print(f"SQS ARN: {SQS_ARN}")
        print(f"Headers: {self.request_headers}")
        print(f"Payload: {json.dumps(self.subscription_payload, indent=2)}")

        if response.status_code in (200, 201):
            return response.json()
        elif response.status_code == 409:
            msg = "SQS Queue Already Subscribed, can't re-subscribe"
            raise UnhandledResponseError(response=response.json(), message=msg)
        elif response.status_code == 401:
            msg = "SQS Queue Already Subscribed, can't re-subscribe"
            raise TokenValidationError(response=response.json(), message=msg)
        elif response.status_code == 400:
            msg = "Resource Type provided for this is not correct"
            raise ResourceFoundError(response=response.json(), message=msg)
        elif response.status_code == 403:
            msg = "You don't have the right permissions for this request"
            raise UnauthorizedError(response=response.json(), message=msg)
        elif response.status_code == 500:
            msg = "Internal Server Error"
            raise ServerError(response=response.json(), message=msg)
        else:
            msg = f"Unhandled error: {response.status_code} - {response.text}"
            raise UnhandledResponseError(response=response.json(), message=msg)

    def get_subscription(self) -> dict | None:
        response = requests.get(MNS_URL, headers=self.request_headers)
        logging.info(f"GET {MNS_URL}")
        logging.debug(f"Headers: {self.request_headers}")

        if response.status_code == 200:
            bundle = response.json()
            # Assume a FHIR Bundle with 'entry' list
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", entry)
                print(f"get resource sub: {resource}")
                logging.debug(f"get resource sub: {resource}")
                channel = resource.get("channel", {})
                if channel.get("endpoint") == SQS_ARN:
                    return resource  # Found a matching subscription
            return None  # No subscription for this SQS ARN
        elif response.status_code == 401:
            msg = "Token validation failed for the request"
            raise TokenValidationError(response=response.json(), message=msg)
        elif response.status_code == 400:
            msg = "Bad request: Resource type or parameters incorrect"
            raise ResourceFoundError(response=response.json(), message=msg)
        elif response.status_code == 403:
            msg = "You don't have the right permissions for this request"
            raise UnauthorizedError(response=response.json(), message=msg)
        elif response.status_code == 500:
            msg = "Internal Server Error"
            raise ServerError(response=response.json(), message=msg)
        else:
            msg = f"Unhandled error: {response.status_code} - {response.text}"
            raise UnhandledResponseError(response=response.json(), message=msg)

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

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete the subscription by ID."""
        url = f"{MNS_URL}/{subscription_id}"
        response = requests.delete(url, headers=self.request_headers)
        if response.status_code in (200, 204):
            logging.info(f"Deleted subscription {subscription_id}")
            return True
        elif response.status_code == 401:
            raise TokenValidationError(response=response.json(), message="Token validation failed for the request")
        elif response.status_code == 404:
            raise ResourceFoundError(response=response.json(), message=f"Subscription {subscription_id} not found")
        elif response.status_code == 403:
            raise UnauthorizedError(response=response.json(), message="No permission to delete subscription")
        elif response.status_code == 500:
            raise ServerError(response=response.json(), message="Internal Server Error")
        else:
            raise UnhandledResponseError(response=response.json(), message=f"Unhandled error: {response.status_code}")

    def check_delete_subcription(self):
        try:
            resource = self.get_subscription()  # Get the full resource dict
            if not resource:
                return "No matching subscription found to delete."

            subscription_id = resource.get("id")
            if not subscription_id:
                return "Subscription resource missing 'id' field."

            self.delete_subscription(subscription_id)
            return "Subscription successfully deleted"
        except Exception as e:
            # Optionally log the exception here
            return f"Error deleting subscription: {str(e)}"
