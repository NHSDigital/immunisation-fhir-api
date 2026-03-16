import json
import os
import random
import uuid
from pathlib import Path
from urllib.parse import urlencode

from locust import HttpUser, constant_throughput, task

from common.api_clients.authentication import AppRestrictedAuth
from common.clients import get_secrets_manager_client
from objectModels import patient_loader
from objectModels.api_immunization_builder import create_immunization_object
from objectModels.patient_loader import load_patient_by_id

CONTENT_TYPE_FHIR_JSON = "application/fhir+json"
SNOMED_SYSTEM = "http://snomed.info/sct"

APIGEE_ENVIRONMENT = os.getenv("APIGEE_ENVIRONMENT")
if not APIGEE_ENVIRONMENT:
    raise ValueError("APIGEE_ENVIRONMENT must be set")

PERF_SUPPLIER_SYSTEM = os.getenv("PERF_SUPPLIER_SYSTEM", "EMIS").upper()
PERF_CREATE_RPS_PER_USER = float(os.getenv("PERF_CREATE_RPS_PER_USER", "1"))
PERF_CREATE_VACCINE_TYPE = os.getenv("PERF_CREATE_VACCINE_TYPE", "COVID").upper()

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

NHS_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"

patient_loader.csv_path = str(Path(__file__).resolve().parents[2] / "e2e_automation" / "input" / "testData.csv")


class BaseImmunizationUser(HttpUser):
    abstract = True

    authenticator = AppRestrictedAuth(
        get_secrets_manager_client(),
        APIGEE_ENVIRONMENT,
        f"imms/perf-tests/{APIGEE_ENVIRONMENT}/jwt-secrets",
    )
    host = f"https://{APIGEE_ENVIRONMENT}.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"

    def get_headers(self):
        return {
            "Accept": CONTENT_TYPE_FHIR_JSON,
            "Authorization": f"Bearer {self.authenticator.get_access_token()}",
            "Content-Type": CONTENT_TYPE_FHIR_JSON,
            "SupplierSystem": PERF_SUPPLIER_SYSTEM,
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
        }

    def _build_create_payload(self):
        immunization_target = random.choice(IMMUNIZATION_TARGETS)
        patient = load_patient_by_id("Random")
        immunization = create_immunization_object(patient, immunization_target)
        return json.loads(immunization.json(exclude_none=True))

    def _delete_created_immunization(self, immunization_id: str):
        headers = self.get_headers()
        with self.client.delete(
            f"/Immunization/{immunization_id}",
            headers=headers,
            name="Delete Immunization Cleanup",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 202, 204):
                response.success()
            else:
                response.failure(f"Cleanup delete failed for {immunization_id}: {response.status_code} {response.text}")


class SearchUser(BaseImmunizationUser):
    wait_time = constant_throughput(1)

    @task
    def search_single_vacc_type(self):
        nhs_number = random.choice(NHS_NUMBERS)
        immunization_target = random.choice(IMMUNIZATION_TARGETS)
        query = urlencode(
            {
                "patient.identifier": f"{NHS_SYSTEM}|{nhs_number}",
                "-immunization.target": immunization_target,
            }
        )
        self.client.get(
            f"/Immunization?{query}",
            headers=self.get_headers(),
            name="Search Single Vaccine Type",
        )

    @task
    def search_multiple_vacc_types(self):
        nhs_number = random.choice(NHS_NUMBERS)
        query = urlencode(
            {
                "patient.identifier": f"{NHS_SYSTEM}|{nhs_number}",
                "-immunization.target": ",".join(IMMUNIZATION_TARGETS),
            }
        )
        self.client.get(
            f"/Immunization?{query}",
            headers=self.get_headers(),
            name="Search Multiple Vaccine Types",
        )


class CreateUser(BaseImmunizationUser):
    wait_time = constant_throughput(PERF_CREATE_RPS_PER_USER)

    @task
    def create_immunization(self):
        payload = self._build_create_payload()
        headers = self.get_headers()

        with self.client.post(
            "/Immunization",
            json=payload,
            headers=headers,
            name="Create Immunization",
            catch_response=True,
        ) as response:
            location = response.headers.get("Location") or response.headers.get("location")
            response.success()

            created_id = location.rstrip("/").split("/")[-1]
            if created_id:
                self._delete_created_immunization(created_id)
