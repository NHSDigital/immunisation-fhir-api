import json
import math
import os
import random
import uuid
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from locust import HttpUser, LoadTestShape, constant_throughput, task

from common.api_clients.authentication import AppRestrictedAuth
from common.clients import get_secrets_manager_client
from common.models.constants import Urls
from objectModels import patient_loader
from objectModels.api_immunization_builder import create_immunization_object
from objectModels.patient_loader import load_patient_by_id

CONTENT_TYPE_FHIR_JSON = "application/fhir+json"

APIGEE_ENVIRONMENT = os.getenv("APIGEE_ENVIRONMENT", "ref")
if not APIGEE_ENVIRONMENT:
    raise ValueError("APIGEE_ENVIRONMENT must be set")

PERF_CREATE_TASK_RPS_PER_USER = float(os.getenv("PERF_CREATE_RPS_PER_USER", "1"))
PERF_LOAD_PROFILE = os.getenv("PERF_LOAD_PROFILE", "").strip().lower()
PERF_BASELINE_RPS = int(os.getenv("PERF_BASELINE_RPS", "125"))
PERF_BASELINE_DURATION_SECONDS = int(os.getenv("PERF_BASELINE_DURATION_SECONDS", "300"))
PERF_SPIKE_WARMUP_RPS = int(os.getenv("PERF_SPIKE_WARMUP_RPS", "125"))
PERF_SPIKE_RPS = int(os.getenv("PERF_SPIKE_RPS", "460"))
PERF_SPIKE_WARMUP_SECONDS = int(os.getenv("PERF_SPIKE_WARMUP_SECONDS", "120"))
PERF_SPIKE_DURATION_SECONDS = int(os.getenv("PERF_SPIKE_DURATION_SECONDS", "60"))
PERF_SPIKE_RECOVERY_SECONDS = int(os.getenv("PERF_SPIKE_RECOVERY_SECONDS", "120"))
PERF_RAMP_START_RPS = int(os.getenv("PERF_RAMP_START_RPS", "50"))
PERF_RAMP_STEP_RPS = int(os.getenv("PERF_RAMP_STEP_RPS", "25"))
PERF_RAMP_MAX_RPS = int(os.getenv("PERF_RAMP_MAX_RPS", "500"))
PERF_RAMP_STEP_DURATION_SECONDS = int(os.getenv("PERF_RAMP_STEP_DURATION_SECONDS", "60"))

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

CREATE_SUCCESS_STATUSES = {200, 201, 202}
DELETE_SUCCESS_STATUSES = {200, 202, 204}

patient_loader.csv_path = str(Path(__file__).resolve().parents[2] / "e2e_automation" / "input" / "testData.csv")


def _load_valid_patients():
    patient_df = pd.read_csv(patient_loader.csv_path, dtype=str)
    valid_patients = patient_df[patient_df["id"] == "Valid_NHS"]["nhs_number"].tolist()
    if not valid_patients:
        raise ValueError(f"No valid patients found in {patient_loader.csv_path}")
    return valid_patients


VALID_PATIENT_IDS = _load_valid_patients()


def _users_for_target_rps(target_rps: int) -> int:
    per_user_rps = PERF_CREATE_TASK_RPS_PER_USER if PERF_CREATE_TASK_RPS_PER_USER > 0 else 1
    return max(1, math.ceil(target_rps / per_user_rps))


class CampaignCapacityShape(LoadTestShape):
    abstract = PERF_LOAD_PROFILE not in {"baseline", "spike", "ramp"}

    def tick(self):
        run_time = self.get_run_time()

        if PERF_LOAD_PROFILE == "baseline":
            if run_time >= PERF_BASELINE_DURATION_SECONDS:
                return None
            target_rps = PERF_BASELINE_RPS
        elif PERF_LOAD_PROFILE == "spike":
            if run_time < PERF_SPIKE_WARMUP_SECONDS:
                target_rps = PERF_SPIKE_WARMUP_RPS
            elif run_time < PERF_SPIKE_WARMUP_SECONDS + PERF_SPIKE_DURATION_SECONDS:
                target_rps = PERF_SPIKE_RPS
            elif run_time < PERF_SPIKE_WARMUP_SECONDS + PERF_SPIKE_DURATION_SECONDS + PERF_SPIKE_RECOVERY_SECONDS:
                target_rps = PERF_SPIKE_WARMUP_RPS
            else:
                return None
        else:
            current_step = int(run_time // PERF_RAMP_STEP_DURATION_SECONDS)
            target_rps = PERF_RAMP_START_RPS + (current_step * PERF_RAMP_STEP_RPS)
            if target_rps > PERF_RAMP_MAX_RPS:
                return None

        user_count = _users_for_target_rps(target_rps)
        return user_count, user_count


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
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
        }

    def _build_create_payload(self):
        immunization_target = random.choice(IMMUNIZATION_TARGETS)
        patient = load_patient_by_id(random.choice(VALID_PATIENT_IDS))
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
            if response.status_code in DELETE_SUCCESS_STATUSES:
                response.success()
            else:
                response.failure(f"Cleanup delete failed for {immunization_id}: {response.status_code} {response.text}")


class SearchUser(BaseImmunizationUser):
    wait_time = constant_throughput(1)

    @task
    def search_single_vacc_type(self):
        nhs_number = random.choice(VALID_PATIENT_IDS)
        immunization_target = random.choice(IMMUNIZATION_TARGETS)
        query = urlencode(
            {
                "patient.identifier": f"{Urls.NHS_NUMBER}|{nhs_number}",
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
        nhs_number = random.choice(VALID_PATIENT_IDS)
        query = urlencode(
            {
                "patient.identifier": f"{Urls.NHS_NUMBER}|{nhs_number}",
                "-immunization.target": ",".join(IMMUNIZATION_TARGETS),
            }
        )
        self.client.get(
            f"/Immunization?{query}",
            headers=self.get_headers(),
            name="Search Multiple Vaccine Types",
        )


class CreateUser(BaseImmunizationUser):
    wait_time = constant_throughput(PERF_CREATE_TASK_RPS_PER_USER)

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
            if response.status_code not in CREATE_SUCCESS_STATUSES:
                response.failure(f"Create failed: {response.status_code} {response.text}")
                return

            location = response.headers.get("Location") or response.headers.get("location")
            if not location:
                response.failure("Create succeeded without a Location header; cleanup skipped")
                return

            created_id = location.rstrip("/").split("/")[-1]
            if not created_id:
                response.failure(f"Create returned an invalid Location header: {location}")
                return

            response.success()
            self._delete_created_immunization(created_id)
