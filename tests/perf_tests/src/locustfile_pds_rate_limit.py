import math
import os
import random
from urllib.parse import urlparse

from locust import HttpUser, LoadTestShape, constant_throughput, task

PERF_LOAD_PROFILE = os.getenv("PERF_LOAD_PROFILE", "").strip().lower()
MOCK_PDS_BASE_URL = os.getenv("MOCK_PDS_BASE_URL", "http://127.0.0.1:18080").strip().rstrip("/")


def _validate_mock_pds_base_url(base_url: str) -> str:
    if "<" in base_url or ">" in base_url:
        raise ValueError(
            "MOCK_PDS_BASE_URL still contains a placeholder. Set it to the real Lambda Function URL, "
            "for example https://abc123.lambda-url.eu-west-2.on.aws"
        )

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "MOCK_PDS_BASE_URL must be a valid absolute URL, for example https://abc123.lambda-url.eu-west-2.on.aws"
        )

    return base_url


MOCK_PDS_BASE_URL = _validate_mock_pds_base_url(MOCK_PDS_BASE_URL)

PERF_MOCK_PDS_RPS_PER_USER = float(os.getenv("PERF_MOCK_PDS_RPS_PER_USER", "1"))
MOCK_PDS_VERIFY_TLS = os.getenv("MOCK_PDS_VERIFY_TLS", "false").strip().lower() in {"1", "true", "yes"}

PERF_MOCK_PDS_AVERAGE_RPS = int(os.getenv("PERF_MOCK_PDS_AVERAGE_RPS", "140"))
PERF_MOCK_PDS_AVERAGE_DURATION_SECONDS = int(os.getenv("PERF_MOCK_PDS_AVERAGE_DURATION_SECONDS", "180"))

PERF_MOCK_PDS_SPIKE_WARMUP_RPS = int(os.getenv("PERF_MOCK_PDS_SPIKE_WARMUP_RPS", "125"))
PERF_MOCK_PDS_SPIKE_RPS = int(os.getenv("PERF_MOCK_PDS_SPIKE_RPS", "460"))
PERF_MOCK_PDS_SPIKE_WARMUP_SECONDS = int(os.getenv("PERF_MOCK_PDS_SPIKE_WARMUP_SECONDS", "10"))
PERF_MOCK_PDS_SPIKE_DURATION_SECONDS = int(os.getenv("PERF_MOCK_PDS_SPIKE_DURATION_SECONDS", "20"))
PERF_MOCK_PDS_SPIKE_RECOVERY_RPS = int(os.getenv("PERF_MOCK_PDS_SPIKE_RECOVERY_RPS", "125"))
PERF_MOCK_PDS_SPIKE_RECOVERY_SECONDS = int(os.getenv("PERF_MOCK_PDS_SPIKE_RECOVERY_SECONDS", "10"))

RATE_LIMIT_MESSAGE = "Mock PDS rate limit has been exceeded"


def _users_for_target_rps(target_rps: int) -> int:
    per_user_rps = PERF_MOCK_PDS_RPS_PER_USER if PERF_MOCK_PDS_RPS_PER_USER > 0 else 1
    return max(1, math.ceil(target_rps / per_user_rps))


class MockPdsRateLimitShape(LoadTestShape):
    abstract = PERF_LOAD_PROFILE not in {"average", "spike"}

    def tick(self):
        run_time = self.get_run_time()

        if PERF_LOAD_PROFILE == "average":
            if run_time >= PERF_MOCK_PDS_AVERAGE_DURATION_SECONDS:
                return None
            target_rps = PERF_MOCK_PDS_AVERAGE_RPS
        elif PERF_LOAD_PROFILE == "spike":
            spike_end = PERF_MOCK_PDS_SPIKE_WARMUP_SECONDS + PERF_MOCK_PDS_SPIKE_DURATION_SECONDS
            recovery_end = spike_end + PERF_MOCK_PDS_SPIKE_RECOVERY_SECONDS

            if run_time < PERF_MOCK_PDS_SPIKE_WARMUP_SECONDS:
                target_rps = PERF_MOCK_PDS_SPIKE_WARMUP_RPS
            elif run_time < spike_end:
                target_rps = PERF_MOCK_PDS_SPIKE_RPS
            elif run_time < recovery_end:
                target_rps = PERF_MOCK_PDS_SPIKE_RECOVERY_RPS
            else:
                return None
        else:
            return None

        user_count = _users_for_target_rps(target_rps)
        return user_count, user_count


class MockPdsUser(HttpUser):
    wait_time = constant_throughput(PERF_MOCK_PDS_RPS_PER_USER)
    host = MOCK_PDS_BASE_URL

    def on_start(self):
        self.client.verify = MOCK_PDS_VERIFY_TLS

    @staticmethod
    def _random_nhs_number() -> str:
        return f"99{random.randint(10_000_000, 99_999_999)}"

    @task
    def get_patient(self):
        with self.client.get(
            f"/Patient/{self._random_nhs_number()}",
            headers={"Accept": "application/fhir+json"},
            name="Mock PDS Patient Lookup",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                return

            if response.status_code == 429:
                try:
                    payload = response.json()
                except ValueError:
                    response.failure(f"429 response was not valid JSON: {response.text}")
                    return

                if payload.get("code") == 429 and payload.get("message") == RATE_LIMIT_MESSAGE:
                    response.failure(f"HTTP {response.status_code}: {RATE_LIMIT_MESSAGE}")
                else:
                    response.failure(f"Unexpected 429 payload: {response.text}")
                return

            if response.status_code == 0:
                error_detail = getattr(response, "error", None)
                response.failure(
                    "Connection failed before reaching mock PDS. "
                    f"Check MOCK_PDS_BASE_URL={self.host}. "
                    f"TLS verification enabled={MOCK_PDS_VERIFY_TLS}. "
                    f"Underlying error: {error_detail!r}"
                )
                return

            response.failure(f"Unexpected response: {response.status_code} {response.text}")
