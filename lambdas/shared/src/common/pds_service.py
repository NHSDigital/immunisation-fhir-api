import uuid

import requests

from common.authentication import AppRestrictedAuth
from common.clients import logger
from common.models.errors import UnhandledResponseError


class PdsService:
    def __init__(self, authenticator: AppRestrictedAuth, environment):
        logger.info(f"PdsService init: {environment}")
        self.authenticator = authenticator

        self.base_url = (
            f"https://{environment}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
            if environment != "prod"
            else "https://api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
        )

        logger.info(f"PDS Service URL: {self.base_url}")

    def get_patient_details(self, patient_id: str) -> dict | None:
        access_token = self.authenticator.get_access_token()
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Correlation-ID": str(uuid.uuid4()),
        }
        response = requests.get(f"{self.base_url}/{patient_id}", headers=request_headers, timeout=5)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.info("Patient not found")
            return None
        elif response.status_code in (400, 401, 403):
            logger.info(f"PDS Client Error: Status = {response.status_code} - Body {response.text}")
            msg = "Client error occurred while calling PDS"
            raise UnhandledResponseError(response=response.json(), message=msg)
        elif response.status_code in (500, 502, 503, 504):
            logger.error(f"PDS Server Error: Status = {response.status_code} - Body {response.text}")
            msg = "Server error occurred while calling PDS"
            raise UnhandledResponseError(response=response.json(), message=msg)
        else:
            logger.error(f"PDS. Error response: {response.status_code} - {response.text}")
            msg = "Downstream service failed to validate the patient"
            raise UnhandledResponseError(response=response.json(), message=msg)
