import requests
import os
import uuid
import logging
import json
from authentication import AppRestrictedAuth
from models.errors import UnhandledResponseError

SQS_ARN = os.getenv("SQS_ARN")
MNS_URL = "https://int.api.service.nhs.uk/multicast-notification-service/subscriptions"


class MnsService:
    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator

        logging.info(f"Using SQS ARN for subscription: {SQS_ARN}")

    def subscribe_notification(self) -> dict | None:
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Content-Type': 'application/fhir+json',
            'Authorization': f'Bearer {access_token}',
            'X-Correlation-ID': str(uuid.uuid4())
        }

        subscription_payload = {
            "resourceType": "Subscription",
            "status": "requested",
            "reason": "Subscribe SQS to MNS test-signal",
            "criteria": "eventType=nhs-number-change-2",
            "channel": {
                "type": "message",
                "endpoint": SQS_ARN,
                "payload": "application/json"
                }
            }
        response = requests.post(MNS_URL, headers=request_headers, data=json.dumps(subscription_payload))

        print(f"Access Token: {access_token}")
        print(f"SQS ARN: {SQS_ARN}")
        print(f"Headers: {request_headers}")
        print(f"Payload: {json.dumps(subscription_payload, indent=2)}")

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            msg = "MNS subscription failed"
            raise UnhandledResponseError(response=response.json(), message=msg)
