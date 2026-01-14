import os

import pytest
import requests
from pytest_bdd import scenarios, then, when
from utilities.context import ScenarioContext
from utilities.http_requests_session import http_requests_session

scenarios("APITests/status.feature")

CONNECTION_ABORTED_ERROR_MSG = "<ExceptionInfo ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))) tblen=6>"


@when("I send a request to the ping endpoint")
def send_request_to_ping_endpoint(context: ScenarioContext) -> None:
    context.response = http_requests_session.get(context.baseUrl + "/_ping")


@when("I send a request to the status endpoint")
def send_request_status_endpoint(context: ScenarioContext) -> None:
    # Let exception be raised if expected env var is not present
    status_api_key: str = os.environ["STATUS_API_KEY"]
    context.response = http_requests_session.get(context.baseUrl + "/_status", headers={"apikey": status_api_key})


@when("I send a direct request to the AWS backend")
def send_request_to_aws_backend(context: ScenarioContext) -> None:
    # Let exception be raised if expected env var is not present
    aws_domain_name: str = os.environ["AWS_DOMAIN_NAME"]
    backend_status_url = aws_domain_name + "/status"

    with pytest.raises(requests.exceptions.ConnectionError) as e:
        requests.get(backend_status_url)

    context.response = str(e)


@when("I send an unauthenticated request to the API")
def send_unauthenticated_request_to_api(context: ScenarioContext) -> None:
    context.response = http_requests_session.get(context.baseUrl + "/Immunization")


@then("The status response will contain a passing healthcheck")
def check_status_response_healthy(context: ScenarioContext) -> None:
    status_response = context.response.json()
    assertion_failure_msg = f"Status response assertions failed. Res: {status_response}"

    assert status_response.get("status") == "pass", assertion_failure_msg
    assert status_response.get("checks", {}).get("healthcheck", {}).get("status") == "pass", assertion_failure_msg


@then("The request is rejected")
def check_the_direct_req_is_rejected(context: ScenarioContext) -> None:
    assert context.response == CONNECTION_ABORTED_ERROR_MSG, f"got unexpected mTLS error msg: {context.response}"
