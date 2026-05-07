import uuid

from common.api_clients.authentication import AppRestrictedAuth
from common.api_clients.errors import raise_error_response
from common.api_clients.retry import request_with_retry_backoff
from common.clients import logger


class PdsService:
    def __init__(
        self,
        authenticator: AppRestrictedAuth | None,
        environment: str,
        base_url: str | None = None,
    ):
        logger.info(f"PdsService init: {environment}")
        self.authenticator = authenticator
        host = "api.service.nhs.uk" if environment == "prod" else f"{environment}.api.service.nhs.uk"
        self.base_url = base_url.rstrip("/") if base_url else f"https://{host}/personal-demographics/FHIR/R4/Patient"
        logger.info(f"PDS Service URL: {self.base_url}")

    def get_patient_details(self, patient_id: str) -> dict | None:
        headers = {"X-Request-ID": str(uuid.uuid4()), "X-Correlation-ID": str(uuid.uuid4())}
        if self.authenticator is not None:
            headers["Authorization"] = f"Bearer {self.authenticator.get_access_token()}"

        response = request_with_retry_backoff("GET", f"{self.base_url}/{patient_id}", headers=headers)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            logger.info("Patient not found")
            return None
        raise_error_response(response)
