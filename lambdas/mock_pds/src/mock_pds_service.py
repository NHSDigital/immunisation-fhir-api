import json
import logging
from http import HTTPStatus

from rate_limiter import FixedWindowRateLimiter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

FHIR_JSON_CONTENT_TYPE = "application/fhir+json"
JSON_CONTENT_TYPE = "application/json"
RATE_LIMIT_MESSAGE = "Mock PDS rate limit has been exceeded"


class MockPdsService:
    def __init__(self, rate_limiter: FixedWindowRateLimiter, gp_ods_code: str):
        self.rate_limiter = rate_limiter
        self.gp_ods_code = gp_ods_code

    def handle(self, event: dict) -> dict:
        method = self._get_method(event)
        if method != "GET":
            return self._json_response(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"code": HTTPStatus.METHOD_NOT_ALLOWED, "message": "Method not allowed"},
            )

        nhs_number = self._extract_patient_id(event)
        if not nhs_number:
            return self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"code": HTTPStatus.BAD_REQUEST, "message": "Patient id is required"},
            )

        decision = self.rate_limiter.check("patient-lookup")
        if not decision.allowed:
            logger.warning(
                "Mock PDS rate limit exceeded for %s window: count=%s limit=%s window_seconds=%s",
                decision.window_name,
                decision.count,
                decision.limit,
                decision.window_seconds,
            )
            return self._json_response(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"code": HTTPStatus.TOO_MANY_REQUESTS, "message": RATE_LIMIT_MESSAGE},
            )

        logger.info("Mock PDS served patient lookup for nhs_number=%s", nhs_number)
        return self._json_response(
            HTTPStatus.OK,
            self._build_patient(nhs_number),
            content_type=FHIR_JSON_CONTENT_TYPE,
        )

    def _build_patient(self, nhs_number: str) -> dict:
        suffix = nhs_number[-4:] if nhs_number else "0000"
        day = max(1, (int(suffix[-2:]) % 28))
        month = max(1, (int(suffix[:2]) % 12))

        return {
            "resourceType": "Patient",
            "id": nhs_number,
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": nhs_number,
                }
            ],
            "birthDate": f"1985-{month:02d}-{day:02d}",
            "gender": "unknown",
            "name": [
                {
                    "family": f"Mock-{suffix}",
                    "given": ["Ref", "Patient"],
                }
            ],
            "generalPractitioner": [
                {
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": self.gp_ods_code,
                        "period": {
                            "start": "2024-01-01",
                        },
                    }
                }
            ],
        }

    @staticmethod
    def _get_method(event: dict) -> str:
        request_context = event.get("requestContext", {})
        http_context = request_context.get("http", {})
        return http_context.get("method") or event.get("httpMethod") or "GET"

    @staticmethod
    def _extract_patient_id(event: dict) -> str | None:
        path = (
            event.get("rawPath") or event.get("path") or event.get("requestContext", {}).get("http", {}).get("path", "")
        )
        normalized_path = path.rstrip("/")

        if "/Patient/" not in normalized_path:
            return None

        return normalized_path.rsplit("/Patient/", maxsplit=1)[-1] or None

    @staticmethod
    def _json_response(status_code: int, body: dict, content_type: str = JSON_CONTENT_TYPE) -> dict:
        return {
            "statusCode": status_code,
            "headers": {"Content-Type": content_type},
            "body": json.dumps(body),
        }
