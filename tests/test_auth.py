import pytest
import requests
from .configuration import config
from .example_loader import load_example


@pytest.mark.auth
@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_invalid_operation_returns_400(nhsd_apim_auth_headers):
    endpoint_url = f"{config.BASE_URL}/{config.BASE_PATH}"
    expected_body = load_example("OperationOutcome/400-invalid_operation.json")

    response = requests.get(endpoint_url, headers=nhsd_apim_auth_headers)

    assert response.status_code == 400
    assert response.json() == expected_body


@pytest.mark.auth
@pytest.mark.debug
def test_invalid_access_token():
    expected_status_code = 401
    expected_body = load_example("OperationOutcome/401-invalid_access_token.json")

    response = requests.get(
        url=f"{config.BASE_URL}/{config.BASE_PATH}",
        headers={
            "Authorization": "Bearer invalid_token"
        },
    )
    assert response.status_code == expected_status_code
    assert response.json() == expected_body


@pytest.mark.auth
def test_invalid_access_token_returns_403():
    endpoint_url = f"{config.BASE_URL}/{config.BASE_PATH}"
    expected_body = load_example("OperationOutcome/403-unauthorized.json")
    invalid_token = "invalid-access-token"

    headers = {
        "Authorization": f"Bearer {invalid_token}",
        "X-Request-Id": "c1ab3fba-6bae-4ba4-b257-5a87c44d4a91",
        "X-Correlation-Id": "9562466f-c982-4bd5-bb0e-255e9f5e6689"
    }

    response = requests.get(endpoint_url, headers=headers)

    assert response.status_code == 403
    assert response.json() == expected_body
