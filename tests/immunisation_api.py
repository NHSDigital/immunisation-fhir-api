import re
import uuid
from typing import Optional

import requests


def parse_location(location) -> Optional[str]:
    """parse location header and return resource ID"""
    pattern = r"https://.*\.api\.service\.nhs\.uk/immunisation-fhir-api.*/Immunization/(.+)"
    if match := re.search(pattern, location):
        return match.group(1)
    else:
        return None


class ImmunisationApi:

    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }

    def get_immunization_by_id(self, event_id):
        return requests.get(f"{self.url}/Immunization/{event_id}", headers=self._update_headers())

    def create_immunization(self, imms):
        return requests.post(f"{self.url}/Immunization", headers=self._update_headers(), json=imms)

    def update_immunization(self, imms_id, imms):
        return requests.put(f"{self.url}/Immunization/{imms_id}", headers=self._update_headers(), json=imms)

    def delete_immunization(self, imms_id):
        return requests.delete(f"{self.url}/Immunization/{imms_id}", headers=self._update_headers())

    def search_immunizations(self, nhs_number, disease_type):
        return requests.get(f"{self.url}/Immunization?-nhsNumber={nhs_number}&-diseaseType={disease_type}",
                            headers=self._update_headers())

    def _update_headers(self, headers=None):
        if headers is None:
            headers = {}
        updated = {**self.headers, **{
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
        }}
        return {**updated, **headers}
