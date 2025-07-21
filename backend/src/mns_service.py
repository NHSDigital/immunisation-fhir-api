import requests
import uuid
import json
from authentication import AppRestrictedAuth
from models.errors import UnhandledResponseError

SQS_ARN = "arn:aws:sqs:eu-west-2:345594581768:imms-pr-655-id-sync-queue"
MNS_URL = "https://int.api.service.nhs.uk/multicast-notification-service/subscriptions"

class mnsService:
    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        
        
        
    def subscribeNotification(self)  -> dict | None:
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Correlation-ID': str(uuid.uuid4())
        }
    
        subscription_payload = {
        "resourceType": "Subscription",
        "status": "requested",
        "reason": "Subscribe SQS to MNS test-signal",
        "criteria": "eventType=mns-test-signal-1",
        "channel": {
            "type": "message",
            "endpoint": SQS_ARN,
            "payload": "application/json"
        }
    }
        response = requests.post(MNS_URL, headers=request_headers, data=json.dumps(subscription_payload))

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            msg = "Please provide the correct resource type for this endpoint"
            raise UnhandledResponseError(response=response.json(), message=msg)


    # Unsubscribe to the PR - destroying the notification
    def unsubscribeNotication():
        pass