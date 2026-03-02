import os
import random
from urllib.parse import urlencode

from locust import HttpUser, constant_throughput, task

from common.api_clients.authentication import AppRestrictedAuth
from common.clients import get_secrets_manager_client

CONTENT_TYPE_FHIR_JSON = "application/fhir+json"

IMMUNIZATION_TARGETS = [
    "3IN1",
    "COVID",
    "FLU",
    "HPV",
    "MENACWY",
    "MMR",
    "MMRV",
    "PNEUMOCOCCAL",
    "PERTUSSIS",
    "RSV",
    "SHINGLES",
]

# TODO - run DynamoDB query to populate this list dynamically?
NHS_NUMBERS = [
    "9160742623",
    "9822833040",
    "9406813963",
    "9505768028",
    "9429583158",
    "9728553366",
    "9153271653",
    "9067110124",
    "9244495082",
    "9940401264",
]


class SearchUser(HttpUser):
    environment = os.getenv("APIGEE_ENVIRONMENT")

    authenticator = AppRestrictedAuth(
        get_secrets_manager_client(), environment, f"imms/perf-tests/{environment}/jwt-secrets"
    )

    host = f"https://{environment}.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"

    wait_time = constant_throughput(1)

    def get_headers(self):
        return {
            "Accept": CONTENT_TYPE_FHIR_JSON,
            "Authorization": f"Bearer {self.authenticator.get_access_token()}",
            "Content-Type": CONTENT_TYPE_FHIR_JSON,
        }

    @task
    def search_single_vacc_type(self):
        nhs_number = random.choice(NHS_NUMBERS)
        immunization_target = random.choice(IMMUNIZATION_TARGETS)
        query = urlencode(
            {
                "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
                "-immunization.target": immunization_target,
            }
        )
        self.client.get(f"/Immunization?{query}", headers=self.get_headers())

    @task
    def search_multiple_vacc_types(self):
        nhs_number = random.choice(NHS_NUMBERS)
        query = urlencode(
            {
                "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
                "-immunization.target": ",".join(IMMUNIZATION_TARGETS),
            }
        )
        self.client.get(f"/Immunization?{query}", headers=self.get_headers())
