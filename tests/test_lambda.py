"""
See
https://github.com/NHSDigital/pytest-nhsd-apim/blob/main/tests/test_examples.py
for more ideas on how to test the authorization of your API.
"""
import random
import time

import pytest
import requests
from assertpy import assert_that


def lambda_crud(url, headers):
    timestamp = int(time.time())
    random.seed(timestamp)
    event_id = str(random.randint(0, 1000))

    request_payload = {
        "id": event_id,
        "message": "Hello World"}
    post_response = requests.post(
        url=f"{url}/event",
        headers=headers,
        json=request_payload,
    )
    assert_that(201).is_equal_to(post_response.status_code)

    get_response = requests.get(
        url=f"{url}/event",
        headers=headers,
        params={
            "id": event_id
        }
    )
    assert_that(200).is_equal_to(get_response.status_code)

    delete_response = requests.delete(
        url=f"{url}/event",
        headers=headers,
        params={
            "id": event_id
        }
    )
    assert_that(200).is_equal_to(delete_response.status_code)


@pytest.mark.smoketest
@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_lambda_crud_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """
    Test for the POST,GET and Delete for Lambda endpoints. Using user-restricted auth
    """
    lambda_crud(nhsd_apim_proxy_url, nhsd_apim_auth_headers)


@pytest.mark.smoketest
@pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3"})
def test_lambda_crud_app_restricted(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """
    Test for the POST,GET and Delete for Lambda endpoints. Using app-restricted
    """
    print(nhsd_apim_proxy_url)
    lambda_crud(nhsd_apim_proxy_url, nhsd_apim_auth_headers)
