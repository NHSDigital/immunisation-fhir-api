import pytest
import requests
from .configuration import config
from .example_loader import load_example


@pytest.mark.auth
@pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level0"})
def test_invalid_access_token():
    expected_status_code = 401
    expected_body = load_example("OperationOutcome/401-invalid_access_token.json")

    response = requests.get(
        url=f"{config.BASE_URL}/{config.BASE_PATH}/event",
        headers={
            "Authorization": "",
            "X-Request-Id": "c1ab3fba-6bae-4ba4-b257-5a87c44d4a91",
            "X-Correlation-Id": "9562466f-c982-4bd5-bb0e-255e9f5e6689",
        },
    )

    assert response.status_code == expected_status_code
    assert response.json() == expected_body


@pytest.mark.auth
@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_invalid_endpoint_returns_404(nhsd_apim_auth_headers):
    expected_status_code = 404
    expected_body = load_example("OperationOutcome/404-not_found.json")

    response = requests.get(
        url=f"{config.BASE_URL}/{config.BASE_PATH}/not_found",
        headers=nhsd_apim_auth_headers,
    )

    assert response.status_code == expected_status_code
    assert response.json() == expected_body
