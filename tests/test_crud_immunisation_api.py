import copy
import json
import os
import pprint
import uuid

import pytest

from .configuration.config import valid_nhs_number1, valid_nhs_number_with_s_flag
from .example_loader import load_example
from .immunisation_api import ImmunisationApi, parse_location


def create_an_imms_obj(imms_id: str = str(uuid.uuid4()), nhs_number=valid_nhs_number1) -> dict:
    imms = copy.deepcopy(load_example("Immunization/POST-Immunization.json"))
    imms["id"] = imms_id
    imms["patient"]["identifier"]["value"] = nhs_number

    return imms


def create_a_deleted_imms_resource(imms_api: ImmunisationApi) -> str:
    imms = create_an_imms_obj()
    res = imms_api.create_immunization(imms)
    imms_id = parse_location(res.headers["Location"])

    res = imms_api.delete_immunization(imms_id)
    assert res.status_code == 204

    return imms_id


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_crud_immunization_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms = create_an_imms_obj()

    # CREATE
    result = imms_api.create_immunization(imms)

    assert result.text == ""
    assert result.status_code == 201
    assert "Location" in result.headers

    # READ
    imms_id = parse_location(result.headers["Location"])

    result = imms_api.get_immunization_by_id(imms_id)
    res_body = result.json()

    assert result.status_code == 200
    assert res_body["id"] == imms_id

    # UPDATE
    update_payload = copy.deepcopy(imms)
    update_payload["id"] = imms_id
    update_payload["status"] = "not-done"
    result = imms_api.update_immunization(imms_id, update_payload)

    assert result.status_code == 200

    # read it back
    result = imms_api.get_immunization_by_id(imms_id)
    res_body = result.json()
    assert res_body["status"] == "not-done"

    # DELETE
    result = imms_api.delete_immunization(imms_id)

    assert result.status_code == 204


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_get_event_by_id_not_found_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    # Arrange
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    # Act
    result = imms_api.get_immunization_by_id("some-id-that-does-not-exist")
    if result.status_code != 404:
        print(result.text)
    res_body = result.json()

    # Assert
    assert result.status_code == 404
    assert res_body["resourceType"] == "OperationOutcome"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_get_event_by_id_invalid_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    # Arrange
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    # Act
    result = imms_api.get_immunization_by_id("some_id_that_is_malformed")
    res_body = result.json()

    # Assert
    assert result.status_code == 400
    assert res_body["resourceType"] == "OperationOutcome"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_delete_immunization_already_deleted(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    # Arrange
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms_id = create_a_deleted_imms_resource(imms_api)

    # Act
    result = imms_api.delete_immunization(imms_id)
    json_result = result.json()

    # Assert
    assert result.status_code == 404
    assert json_result["resourceType"] == "OperationOutcome"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_get_deleted_immunization(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    # Arrange
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms_id = create_a_deleted_imms_resource(imms_api)

    # Act
    result = imms_api.get_immunization_by_id(imms_id)
    json_result = result.json()

    # Assert
    assert result.status_code == 404
    assert json_result["resourceType"] == "OperationOutcome"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_update_none_existing_record_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """update a record that doesn't exist should create a new record"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms_id = str(uuid.uuid4())
    imms = create_an_imms_obj(imms_id)
    result = imms_api.update_immunization(imms_id, imms)
    assert result.status_code == 201


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_update_inconsistent_id_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """update should fail if id in the path doesn't match with the id in the message"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    msg_id = str(uuid.uuid4())
    imms = create_an_imms_obj(msg_id)

    path_id = str(uuid.uuid4())
    result = imms_api.update_immunization(path_id, imms)
    json = result.json()

    assert result.status_code == 400
    assert json["resourceType"] == "OperationOutcome"
    assert path_id in json["issue"][0]["diagnostics"]


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_update_deleted_imms_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """updating deleted record will undo the delete"""
    # This behaviour is consistent. Getting a deleted record will result in a 404. An update of a non-existent record
    #  should result in creating a new record
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms = create_an_imms_obj()

    # first create and then delete
    result = imms_api.create_immunization(imms)
    assert result.status_code == 201

    imms_id = parse_location(result.headers["Location"])
    result = imms_api.delete_immunization(imms_id)
    assert result.status_code == 204

    # When
    imms["id"] = imms_id
    result = imms_api.update_immunization(imms_id, imms)

    # Then
    assert result.status_code == 201


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_bad_nhs_number_nhs_login(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    imms = create_an_imms_obj(nhs_number="7463384756")

    # CREATE
    result = imms_api.create_immunization(imms)
    res_body = result.json()

    assert result.status_code == 400
    assert res_body["resourceType"] == "OperationOutcome"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
@pytest.mark.parametrize("nhs_number,is_restricted", [(valid_nhs_number_with_s_flag, True), (valid_nhs_number1, False)])
def test_get_s_flag_patient(nhsd_apim_proxy_url, nhsd_apim_auth_headers, nhs_number, is_restricted):
    # Arrange
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)

    # Act
    # TODO: Replace this with the usual specification example when it is updated.
    current_directory = os.path.dirname(os.path.realpath(__file__))
    with open(f"{current_directory}/../lambda_code/tests/sample_data/sample_immunization_event.json") as f:
        imms_to_create = json.load(f)
    imms_to_create["patient"]["identifier"]["value"] = nhs_number

    created_imms_result = imms_api.create_immunization(imms_to_create)
    if created_imms_result.status_code != 201:
        pprint.pprint(created_imms_result.text)
        assert created_imms_result.status_code == 201

    created_imms_id = parse_location(created_imms_result.headers["Location"])
    # Read the created resource back to get the full resource
    created_imms = imms_api.get_immunization_by_id(created_imms_id)
    if created_imms.status_code != 200:
        print(created_imms.text)
        assert created_imms.status_code == 200
    created_imms = created_imms.json()

    retrieved_get_imms_result = imms_api.get_immunization_by_id(created_imms["id"])
    if retrieved_get_imms_result.status_code != 200:
        pprint.pprint(retrieved_get_imms_result.text)
        assert retrieved_get_imms_result.status_code == 200
    retrieved_get_imms = retrieved_get_imms_result.json()

    sample_disease_code = 840539006
    retrieved_search_imms_result = imms_api.search_immunizations(nhs_number, sample_disease_code)
    if retrieved_search_imms_result.status_code != 200:
        pprint.pprint(retrieved_search_imms_result.text)
        assert retrieved_search_imms_result.status_code == 200
    retrieved_search_imms = next(imms for imms in retrieved_search_imms_result.json()["entry"]
                                 if imms["resource"]["id"] == created_imms["id"])
    # Fetching Immunization resource form Bundle
    retrieved_search_imms = retrieved_search_imms["resource"]
    all_retrieved_imms = [retrieved_get_imms, retrieved_search_imms]
    imms_api.delete_immunization(created_imms["id"])

    # Assert
    def get_questionnaire_items(imms):
        questionnaire = next(contained for contained in imms["contained"]
                             if contained["questionnaire"] == "Questionnaire/1")
        return questionnaire["item"]

    def assert_is_not_filtered(imms):
        imms_items = get_questionnaire_items(imms)

        for key in ["SiteName", "Consent"]:
            assert key in [item["linkId"] for item in imms_items]

        assert "N2N9I" != next(item for item in imms_items
                               if item["linkId"] == "SiteCode")["answer"][0]["valueCoding"]["code"]
        assert "reportOrigin" in imms
        assert "location" in imms
        assert all(performer["actor"]["identifier"]["value"] != "N2N9I" for performer in imms["performer"])
        assert all(performer["actor"]["identifier"]["system"] != "https://fhir.nhs.uk/Id/ods-organization-code"
                   for performer in imms["performer"])

    def assert_is_filtered(imms):
        imms_items = get_questionnaire_items(imms)

        for key in ["SiteName", "Consent"]:
            assert key not in [item["linkId"] for item in imms_items]

        assert "N2N9I" == next(item for item in imms_items
                               if item["linkId"] == "SiteCode")["answer"][0]["valueCoding"]["code"]
        assert "reportOrigin" not in imms
        assert "location" not in imms
        assert all(performer["actor"]["identifier"]["value"] == "N2N9I" for performer in imms["performer"])
        assert all(performer["actor"]["identifier"]["system"] == "https://fhir.nhs.uk/Id/ods-organization-code"
                   for performer in imms["performer"])

    if is_restricted:
        assert_is_filtered(created_imms)
    else:
        assert_is_not_filtered(created_imms)
    for retrieved_imms in all_retrieved_imms:
        if is_restricted:
            assert_is_filtered(retrieved_imms)
        else:
            assert_is_not_filtered(retrieved_imms)
