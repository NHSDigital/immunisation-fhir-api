import requests
import os
import uuid
import logging
import json
from authentication import AppRestrictedAuth
from models.errors import (
    UnhandledResponseError,
    ResourceNotFoundError,
    UnauthorizedError,
    ServerError,
    BadRequestError,
    TokenValidationError,
    ConflictError
)

SQS_ARN = os.getenv("SQS_ARN")

apigee_env = os.getenv("APIGEE_ENVIRONMENT", "int")
MNS_URL = "https://api.service.nhs.uk/multicast-notification-service/subscriptions" \
    if apigee_env == "prod" else "https://int.api.service.nhs.uk/multicast-notification-service/subscriptions"


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

        response = requests.post(
            MNS_URL, headers=self.request_headers,
            data=json.dumps(self.subscription_payload), timeout=15)
        if response.status_code in (200, 201):
            return response.json()
        else:
            MnsService.handle_response(response)

    def get_subscription(self) -> dict | None:
        response = requests.get(MNS_URL, headers=self.request_headers, timeout=10)
        logging.info(f"GET {MNS_URL}")
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
            MnsService.handle_response(response)

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
        response = requests.delete(url, headers=self.request_headers, timeout=10)
        if response.status_code in (200, 204):
            logging.info(f"Deleted subscription {subscription_id}")
            return True
        else:
            MnsService.handle_response(response)

    def check_delete_subcription(self):
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

    @staticmethod
    def handle_response(response):
        error_mapping = {
            401: (TokenValidationError, "Token validation failed for the request"),
            400: (BadRequestError, "Bad request: Resource type or parameters incorrect"),
            403: (UnauthorizedError, "You don't have the right permissions for this request"),
            500: (ServerError, "Internal Server Error"),
            404: (ResourceNotFoundError, "Subscription or Resource not found"),
            409: (ConflictError, "SQS Queue Already Subscribed, can't re-subscribe")
        }
        exception_class, error_message = error_mapping.get(
            response.status_code,
            (UnhandledResponseError, f"Unhandled error: {response.status_code}"))

        raise exception_class(response=response.json(), message=error_message)
