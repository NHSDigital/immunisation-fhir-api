import requests
import uuid

from common.authentication import AppRestrictedAuth
from common.models.errors import UnhandledResponseError
from common.clients import logger


class PdsService:
    def __init__(self, authenticator: AppRestrictedAuth, environment):
        logger.info(f"PdsService init: {environment}")
        self.authenticator = authenticator

        self.base_url = f"https://{environment}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient" \
            if environment != "prod" else "https://api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"

        logger.info(f"PDS Service URL: {self.base_url}")

    def get_patient_details(self, patient_id) -> dict | None:
        logger.info(f"PDS. Get patient details for ID: {patient_id}")
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Request-ID': str(uuid.uuid4()),
            'X-Correlation-ID': str(uuid.uuid4())
        }
        response = requests.get(f"{self.base_url}/{patient_id}", headers=request_headers, timeout=5)

        if response.status_code == 200:
            logger.info(f"PDS. Response: {response.json()}")
            return response.json()
        elif response.status_code == 404:
            logger.info(f"PDS. Patient not found for ID: {patient_id}")
            return None
        else:
            logger.error(f"PDS. Error response: {response.status_code} - {response.text}")
            msg = "Downstream service failed to validate the patient"
            raise UnhandledResponseError(response=response.json(), message=msg)
