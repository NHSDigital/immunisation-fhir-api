import copy
import uuid
from time import sleep

import pytest

from .configuration.config import valid_nhs_number1, valid_nhs_number2
from .example_loader import load_example
from .immunisation_api import ImmunisationApi, parse_location


def create_immunization(imms_id, nhs_number, disease_code):
    imms = copy.deepcopy(load_example("Immunization/POST-Immunization.json"))
    imms["id"] = imms_id
    imms["patient"]["identifier"]["value"] = nhs_number
    imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = disease_code

    return imms


flu_code = "flue-code-1234"
mmr_code = "mmr-code-2345"
covid_code = "covid-code-7463"


def seed_records(imms_api: ImmunisationApi, records):
    _records = copy.deepcopy(records)
    for record in _records:
        nhs_number = record["nhs_number"]
        for disease in record["diseases"]:
            imms = create_immunization(str(uuid.uuid4()), nhs_number, disease)

            create_res = imms_api.create_immunization(imms)
            assert create_res.status_code == 201
            imms_id = parse_location(create_res.headers["Location"])
            sleep(0.1)
            get_res = imms_api.get_immunization_by_id(imms_id)

            record["responses"].append(get_res.json())

    return _records


def cleanup(imms_api: ImmunisationApi, stored_records: list):
    for record in stored_records:
        for resource in record["responses"]:
            delete_res = imms_api.delete_immunization(resource["id"])
            assert delete_res.status_code == 204
            sleep(0.1)


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_search_immunization(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """it should filter based on disease type"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)
    records = [
        {
            "nhs_number": valid_nhs_number1,
            "diseases": [mmr_code],
            "responses": [],
        },
        {
            "nhs_number": valid_nhs_number1,
            "diseases": [flu_code],
            "responses": [],
        },
        {
            "nhs_number": valid_nhs_number2,
            "diseases": [flu_code, mmr_code, covid_code, mmr_code],
            "responses": [],
        },
    ]
    stored_records = seed_records(imms_api, records)
    # Tests
    # Search patient with multiple disease types
    response = imms_api.search_immunizations(stored_records[0]["nhs_number"], mmr_code)

    cleanup(imms_api, stored_records)

    # Then
    results = response.json()
    result_ids = [result["resource"]["id"] for result in results["entry"]]
    assert response.status_code == 200
    assert results["resourceType"] == "Bundle"
    for resource in stored_records[0]["responses"]:
        assert resource["id"] in result_ids
    for resource in stored_records[1]["responses"]:
        assert resource["id"] not in result_ids


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_search_immunization_ignore_deleted(
    nhsd_apim_proxy_url, nhsd_apim_auth_headers
):
    """it should filter out deleted items"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)
    records = [
        {
            "nhs_number": valid_nhs_number1,
            "diseases": [mmr_code, mmr_code],
            "responses": [],
        },
        {  # same nhs_number but, we will delete it in this test and not during cleanup
            "nhs_number": valid_nhs_number1,
            "diseases": [mmr_code],
            "responses": [],
        },
    ]

    stored_records = seed_records(imms_api, records)

    # Search patient with deleted items
    id_to_delete = stored_records[1]["responses"][0]["id"]
    _ = imms_api.delete_immunization(id_to_delete)

    records = stored_records[0]
    response = imms_api.search_immunizations(records["nhs_number"], mmr_code)

    # pop the one that we already deleted
    stored_records.pop()
    cleanup(imms_api, stored_records)

    # Then
    results = response.json()
    result_ids = [result["resource"]["id"] for result in results["entry"]]

    assert response.status_code == 200
    assert results["resourceType"] == "Bundle"
    assert id_to_delete not in result_ids
    for record in stored_records:
        for resource in record["responses"]:
            assert resource["id"] in result_ids
