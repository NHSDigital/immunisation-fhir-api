import json
import os
import random
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode

import boto3
import gevent.lock
import pandas as pd
from botocore.config import Config
from locust import HttpUser, constant_throughput, events, task

from common.api_clients.authentication import AppRestrictedAuth

# from common.clients import get_secrets_manager_client
from common.models.constants import Urls
from objectModels import patient_loader
from objectModels.api_immunization_builder import create_immunization_object
from objectModels.patient_loader import load_patient_by_id

CONTENT_TYPE_FHIR_JSON = "application/fhir+json"

APIGEE_ENVIRONMENT = os.getenv("APIGEE_ENVIRONMENT", "ref")
if not APIGEE_ENVIRONMENT:
    raise ValueError("APIGEE_ENVIRONMENT must be set")

_BOTO_CONFIG = Config(
    max_pool_connections=50,  # default is 10; needs to exceed max concurrent Locust users
    retries={"mode": "standard", "max_attempts": 3},
)
_secrets_client = boto3.client(
    "secretsmanager",
    region_name=os.getenv("AWS_REGION", "eu-west-2"),
    config=_BOTO_CONFIG,
)

PERF_CREATE_TASK_RPS_PER_USER = float(os.getenv("PERF_CREATE_RPS_PER_USER", "1"))

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

_TOKEN_LOCK = gevent.lock.Semaphore(1)


class LocustTokenManager:
    """Serialises token refreshes across all Locust greenlets (double-checked locking pattern)."""

    def __init__(self, auth: AppRestrictedAuth):
        self._auth = auth

    def get_access_token(self) -> str:
        now = int(time.time())
        # Fast path — no lock needed, reads are safe if the token is already cached
        if (
            self._auth.cached_access_token
            and self._auth.cached_access_token_expiry_time is not None
            and self._auth.cached_access_token_expiry_time > now + 30  # ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS
        ):
            return self._auth.cached_access_token

        # Slow path — exactly one greenlet refreshes; all others wait then hit the fast path
        with _TOKEN_LOCK:
            now = int(time.time())  # re-read after acquiring the lock
            if (
                self._auth.cached_access_token
                and self._auth.cached_access_token_expiry_time is not None
                and self._auth.cached_access_token_expiry_time > now + 30
            ):
                return self._auth.cached_access_token
            return self._auth.get_access_token()


# Module-level singleton — pre-warmed before any user spawns
_shared_token_manager = LocustTokenManager(
    AppRestrictedAuth(
        _secrets_client,
        APIGEE_ENVIRONMENT,
        f"imms/perf-tests/{APIGEE_ENVIRONMENT}/jwt-secrets",
    )
)


@events.init.add_listener
def _pre_warm_auth(environment, **kwargs):
    """Fetch token once before users spawn so all users start with a cached token."""
    try:
        token = _shared_token_manager.get_access_token()
        print(f"[perf] Auth pre-warm complete. Token length: {len(token)}")
    except Exception as exc:
        error_text = str(exc)
        is_credential_error = any(
            kw in error_text for kw in ("ForbiddenException", "ExpiredToken", "No access", "TokenExpired")
        )
        if is_credential_error:
            print(
                "\n[perf] FATAL: AWS credentials expired or inaccessible.\n"
                f"  Error: {exc}\n\n"
                "  Fix: run one of the following, then retry 'make test':\n"
                "    aws sso login --sso-session akshay-sso\n"
                "    aws sso login --profile <your-profile-name>\n",
                file=sys.stderr,
            )
            sys.exit(1)
        # Non-credential error — re-raise so it's not silently swallowed
        raise


class BaseImmunizationUser(HttpUser):
    abstract = True

    # token_manager = LocustTokenManager(
    #     AppRestrictedAuth(
    #         _secrets_client,
    #         APIGEE_ENVIRONMENT,
    #         f"imms/perf-tests/{APIGEE_ENVIRONMENT}/jwt-secrets",
    #     )
    # )

    token_manager = _shared_token_manager
    host = f"https://{APIGEE_ENVIRONMENT}.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"

    def get_headers(self):
        return {
            "Accept": CONTENT_TYPE_FHIR_JSON,
            "Authorization": f"Bearer {self.token_manager.get_access_token()}",
            "Content-Type": CONTENT_TYPE_FHIR_JSON,
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Request-ID": str(uuid.uuid4()),
        }

    def on_start(self):
        # Jitter each user's start by up to 2 s to avoid simultaneous first-request burst
        gevent.sleep(random.uniform(0, 2.0))

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
