import re
import uuid
import time
import random
import requests
from utils.resource import generate_imms_resource, delete_imms_records
from typing import Optional, Literal, List
from datetime import datetime

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
    generated_test_records: List[str]

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
        self.generated_test_records = []

    def __str__(self):
        return f"ImmunizationApi: AuthType: {self.auth}"

    # We implemented this function as a wrapper around the calls to APIGEE
    # in order to prevent build pipelines from failing due to timeouts.
    # The e2e tests put pressure on both test environments from APIGEE and PDS
    # so the chances of having rate limiting errors are high especially during
    # the busy times of the day.
    @staticmethod
    def make_request_with_backoff(
        http_method: str,
        url: str,
        headers: dict = None,
        expected_status_code: int = 200,
        expected_connection_failure: bool = False,
        max_retries: int = 5,
        delay_seconds: float = 2.0,
        **kwargs
    ):
        for attempt in range(max_retries):
            try:
                response = requests.request(method=http_method, url=url, headers=headers, **kwargs)

                # This property is false by default and only true during the mtls test to simulate a connection failure
                if expected_connection_failure:
                    raise RuntimeError(
                        f"Expected the connection to fail, "
                        f"but it succeeded instead.\n"
                        f"Request method: {http_method}\n"
                        f"URL: {url}"
                    )

                # Check if the response matches the expected status code to identify potential issues
                if response.status_code != expected_status_code:
                    if response.status_code >= 500:
                        raise RuntimeError(f"Server error: {response.status_code} during "
                                           f"in {http_method} {url}")
                    else:
                        raise ValueError(f"Expected {expected_status_code} but got "
                                         f"{response.status_code} in {http_method} {url}")

                return response

            except Exception as e:
                if expected_connection_failure or attempt == max_retries - 1:
                    raise

                # This is will be used in the retry logic of the exponential backoff
                wait = (2 ** attempt) + random.uniform(0, 0.5)
                total_wait_time = wait + delay_seconds

                print(
                    f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                    f"[Retry {attempt + 1}] {http_method.upper()} {url} — {e} — retrying in {total_wait_time:.2f}s"
                )

                time.sleep(total_wait_time)

    def create_immunization_resource(self, resource: dict = None) -> str:
        """creates an Immunization resource and returns the resource url"""
        imms = resource if resource else generate_imms_resource()
        response = self.create_immunization(imms)
        assert response.status_code == 201, (response.status_code, response.text)
        return parse_location(response.headers["Location"])

    def create_a_deleted_immunization_resource(self, resource: dict = None) -> dict:
        """it creates a new Immunization and then delete it, it returns the created imms"""
        imms = resource if resource else generate_imms_resource()
        response = self.create_immunization(imms)
        assert response.status_code == 201, response.text
        imms_id = parse_location(response.headers["Location"])
        response = self.delete_immunization(imms_id)
        assert response.status_code == 204, response.text
        imms["id"] = str(uuid.uuid4())

        return imms

    def get_immunization_by_id(self, event_id, expected_status_code: int = 200):
        return self.make_request_with_backoff(
            http_method="GET",
            url=f"{self.url}/Immunization/{event_id}",
            headers=self._update_headers(),
            expected_status_code=expected_status_code
        )

    def create_immunization(self, imms, expected_status_code: int = 201):
        response = self.make_request_with_backoff(
            http_method="POST",
            url=f"{self.url}/Immunization",
            headers=self._update_headers(),
            expected_status_code=expected_status_code,
            json=imms
        )

        if response.status_code == 201:
            if "Location" not in response.headers:
                raise ValueError("Missing 'Location' header in response")

            imms_id = response.headers["Location"].split("Immunization/")[-1]
            if not self._is_valid_uuid4(imms_id):
                raise ValueError(f"Invalid UUID4: {imms_id}")

            self.generated_test_records.append(imms_id)

        return response

    def update_immunization(self, imms_id, imms, expected_status_code: int = 200):
        return self.make_request_with_backoff(
            http_method="PUT",
            url=f"{self.url}/Immunization/{imms_id}",
            headers=self._update_headers(),
            expected_status_code=expected_status_code,
            json=imms
        )

    def delete_immunization(self, imms_id, expected_status_code: int = 204):
        return self.make_request_with_backoff(
            http_method="DELETE",
            url=f"{self.url}/Immunization/{imms_id}",
            headers=self._update_headers(),
            expected_status_code=expected_status_code,
        )

    def search_immunizations(self, patient_identifier: str, immunization_target: str, expected_status_code: int = 200):
        return self.make_request_with_backoff(
            http_method="GET",
            url=f"{self.url}/Immunization?patient.identifier={patient_identifier_system}|{patient_identifier}"
            f"&-immunization.target={immunization_target}",
            headers=self._update_headers(),
            expected_status_code=expected_status_code
        )

    def search_immunizations_full(
            self,
            http_method: Literal["POST", "GET"],
            query_string: Optional[str],
            body: Optional[str],
            expected_status_code: int = 200):

        if http_method == "POST":
            url = f"{self.url}/Immunization/_search?{query_string}"
        else:
            url = f"{self.url}/Immunization?{query_string}"

        return self.make_request_with_backoff(
            http_method=http_method,
            url=url,
            headers=self._update_headers({"Content-Type": "application/x-www-form-urlencoded"}),
            expected_status_code=expected_status_code,
            data=body
        )

    def _update_headers(self, headers=None):
        if headers is None:
            headers = {}
        updated = {**self.headers, **{
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
            "E-Tag": "1"
        }}
        return {**updated, **headers}

    def _is_valid_uuid4(self, imms_id):
        try:
            val = uuid.UUID(imms_id, version=4)
            return str(val) == imms_id
        except ValueError:
            return False

    def cleanup_test_records(self):
        delete_imms_records(self.generated_test_records)
