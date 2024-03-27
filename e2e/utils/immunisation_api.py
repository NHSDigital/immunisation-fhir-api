import re
import uuid
from typing import Optional, Literal

import requests

from lib.authentication import BaseAuthentication
from .constants import patient_identifier_system


def parse_location(location) -> Optional[str]:
    """parse location header and return resource ID"""
    pattern = r"https://.*\.api\.service\.nhs\.uk/immunisation-fhir-api.*/Immunization/(.+)"
    if match := re.search(pattern, location):
        return match.group(1)
    else:
        return None


class ImmunisationApi:
    url: str
    headers: dict
    auth: BaseAuthentication

    def __init__(self, url, auth: BaseAuthentication):
        self.url = url

        self.auth = auth
        # NOTE: this class doesn't support refresh token or expiry check.
        #  This shouldn't be a problem in tests, just something to be aware of
        token = self.auth.get_access_token()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"}

    def __str__(self):
        return f"ImmunizationApi: AuthType: {self.auth}"

    def get_immunization_by_id(self, event_id):
        return requests.get(f"{self.url}/Immunization/{event_id}", headers=self._update_headers())

    def create_immunization(self, imms):
        return requests.post(f"{self.url}/Immunization", headers=self._update_headers(), json=imms)

    def update_immunization(self, imms_id, imms):
        return requests.put(f"{self.url}/Immunization/{imms_id}", headers=self._update_headers(), json=imms)

    def delete_immunization(self, imms_id):
        return requests.delete(f"{self.url}/Immunization/{imms_id}", headers=self._update_headers())

    def search_immunizations(self, patient_identifier: str, immunization_target: str):
        return requests.get(
            f"{self.url}/Immunization?patient.identifier={patient_identifier_system}|{patient_identifier}"
            f"&-immunization.target={immunization_target}",
            headers=self._update_headers())

    def search_immunizations_full(self,
                                  http_method: Literal["POST", "GET"],
                                  query_string: Optional[str],
                                  body: Optional[str]):
        if http_method == "POST":
            url = f"{self.url}/Immunization/_search?{query_string}"
        else:
            url = f"{self.url}/Immunization?{query_string}"
        return requests.request(
            http_method,
            url,
            headers=self._update_headers({"Content-Type": "application/x-www-form-urlencoded"}),
            data=body
        )

    def _update_headers(self, headers=None):
        if headers is None:
            headers = {}
        updated = {**self.headers, **{
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
        }}
        return {**updated, **headers}
