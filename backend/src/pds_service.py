import requests
import uuid

from authentication import AppRestrictedAuth
from models.errors import UnhandledResponseError


class PdsService:
    def __init__(self, authenticator: AppRestrictedAuth, environment):
        self.authenticator = authenticator

        self.base_url = f"https://{environment}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient" \
            if environment != "prod" else "https://api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"

    def get_patient_details(self, patient_id) -> dict | None:
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Request-ID': str(uuid.uuid4()),
            'X-Correlation-ID': str(uuid.uuid4())
        }
        response = requests.get(f"{self.base_url}/{patient_id}", headers=request_headers, timeout=2)
        print(f"PDS_Response:{response}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            msg = "Downstream service failed to validate the patient"
            raise UnhandledResponseError(response=response.json(), message=msg)
