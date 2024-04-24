import requests
import uuid

from authentication import AppRestrictedAuth
from batch.errors import ImmunizationApiUnhandledError, ImmunizationApiError


class ImmunizationApi:
    def __init__(self, authenticator: AppRestrictedAuth, environment):
        self.authenticator = authenticator

        self.base_url = f"https://{environment}.api.service.nhs.uk/immunisation-fhir-api" \
            if environment != "prod" else "https://api.service.nhs.uk/immunisation-fhir-api"

    def create_immunization(self, immunization: dict, correlation_id: str):
        return self._send("POST", "Immunization", immunization, correlation_id)

    def update_immunization(self, immunization: dict, correlation_id: str):
        # TODO: get the id from ???
        imms_id = ""
        return self._send("PUT", f"Immunization/{imms_id}", immunization, correlation_id)

    def delete_immunization(self, immunization: dict, correlation_id: str):
        # TODO: get the id from ???
        imms_id = ""
        return self._send("DELETE", f"Immunization/{imms_id}", immunization, correlation_id)

    def _send(self, method, path, imms, correlation_id):
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Request-ID': str(uuid.uuid4()),
            'X-Correlation-ID': correlation_id,
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        try:
            response = requests.request(method=method, url=f"{self.base_url}/{path}",
                                        headers=request_headers,
                                        json=imms,
                                        timeout=5)
        except Exception as e:
            raise ImmunizationApiUnhandledError(request=imms) from e

        if response.status_code < 300:
            return response
        else:
            raise ImmunizationApiError(
                request=imms, response=response.text,
                status_code=response.status_code)
