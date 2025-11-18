import os
import random
from urllib.parse import urlencode

from locust import HttpUser, constant_throughput, task


class SearchUser(HttpUser):
    wait_time = constant_throughput(1)
    immunization_targets = [
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
    nhs_numbers = [
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

    def on_start(self):
        access_token = os.getenv("APIGEE_ACCESS_TOKEN")
        self.client.headers = {
            "Accept": "application/fhir+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/fhir+json",
        }

    @task
    def search_single_vacc_type(self):
        nhs_number = random.choice(self.nhs_numbers)
        immunization_target = random.choice(self.immunization_targets)
        query = urlencode(
            {
                "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
                "-immunization.target": immunization_target,
            }
        )
        self.client.get(f"/Immunization?{query}")

    @task
    def search_multiple_vacc_types(self):
        nhs_number = random.choice(self.nhs_numbers)
        query = urlencode(
            {
                "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
                "-immunization.target": ",".join(self.immunization_targets),
            }
        )
        self.client.get(f"/Immunization?{query}")
