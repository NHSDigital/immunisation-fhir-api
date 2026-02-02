import uuid

from common.authentication import AppRestrictedAuth
from common.clients import logger
from common.models.api_clients import (
    raise_error_response,
    request_with_retry_backoff,
)


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
        response = request_with_retry_backoff("GET", f"{self.base_url}/{patient_id}", headers=request_headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.info("Patient not found")
            return None
        else:
            raise_error_response(response)
