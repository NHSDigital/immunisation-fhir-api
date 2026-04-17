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

        self.base_url = self._resolve_base_url(environment, base_url)

        logger.info(f"PDS Service URL: {self.base_url}")

    @staticmethod
    def _resolve_base_url(environment: str, base_url: str | None) -> str:
        if base_url:
            return base_url.rstrip("/")

        return (
            f"https://{environment}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
            if environment != "prod"
            else "https://api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
        )

    def get_patient_details(self, patient_id: str) -> dict | None:
        request_headers = {
            "X-Request-ID": str(uuid.uuid4()),
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        if self.authenticator is not None:
            access_token = self.authenticator.get_access_token()
            request_headers["Authorization"] = f"Bearer {access_token}"

        response = request_with_retry_backoff("GET", f"{self.base_url}/{patient_id}", headers=request_headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.info("Patient not found")
            return None
        else:
            raise_error_response(response)
