import uuid
import copy

import pytest

from .configuration.config import valid_nhs_number1
from .example_loader import load_example
from .immunisation_api import ImmunisationApi, parse_location


def create_an_imms_obj(imms_id: str = str(uuid.uuid4()), nhs_number=valid_nhs_number1) -> dict:
    imms = copy.deepcopy(load_example("Immunization/POST-COVID19-Immunization.json"))
    imms["id"] = imms_id
    imms["identifier"][0]["value"] = str(uuid.uuid4())
    imms["contained"][1]["identifier"][0]["value"] = nhs_number
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
    imms["identifier"][0]["value"] = str(uuid.uuid4())

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
    update_payload["status"] = "entered-in-error"
    result = imms_api.update_immunization(imms_id, update_payload)

    assert result.status_code == 200

    # read it back
    result = imms_api.get_immunization_by_id(imms_id)
    res_body = result.json()
    assert res_body["status"] == "entered-in-error"

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
def test_create_immunization_with_stored_identifier_returns_error(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """create should fail if the identifier in the record is not unique"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)
    identifier = str(uuid.uuid4())

    imms = create_an_imms_obj()
    imms["identifier"][0]["value"] = identifier

    # CREATE IMMUNIZATION
    create_response = imms_api.create_immunization(imms)
    assert create_response.status_code == 201
    assert "Location" in create_response.headers

    # CREATE IMMUNIZATION WITH SAME IDENTIFIER
    failed_create_response = imms_api.create_immunization(imms)
    failed_create_res_body = failed_create_response.json()

    assert failed_create_response.status_code == 422
    assert failed_create_res_body["resourceType"] == "OperationOutcome"
    # ASSERT RESPONSE BODY HAS GENERIC ERROR MESSSAGE
    assert failed_create_res_body["issue"][0]["diagnostics"] == "Submitted resource is not valid."

    # READ
    imms_id = parse_location(create_response.headers["Location"])

    # DELETE
    delete_response = imms_api.delete_immunization(imms_id)
    assert delete_response.status_code == 204


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "656005750104"},
    }
)
def test_update_immunization_with_stored_identifier_returns_error(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """update should fail if the identifier in the record is not unique"""
    token = nhsd_apim_auth_headers["Authorization"]
    imms_api = ImmunisationApi(nhsd_apim_proxy_url, token)
    identifier = str(uuid.uuid4())

    imms = create_an_imms_obj()
    imms["identifier"][0]["value"] = identifier

    imms_2 = create_an_imms_obj()
    imms_2["identifier"][0]["value"] = str(uuid.uuid4())

    # CREATE FIRST IMMUNIZATION
    imms_response = imms_api.create_immunization(imms)
    assert imms_response.status_code == 201
    assert "Location" in imms_response.headers

    # CREATE SECOND IMMUNIZATION
    imms_2_response = imms_api.create_immunization(imms_2)
    assert imms_2_response.status_code == 201
    assert "Location" in imms_2_response.headers

    # UPDATE SECOND IMMUNIZATION WITH FIRST IMMUNIZATIONS IDENTIFIER
    updated_imms = copy.deepcopy(imms)
    updated_imms["id"] = imms_2["id"]
    updated_imms["identifier"][0]["value"] = identifier
    update_response = imms_api.update_immunization(imms_2["id"], updated_imms)
    res_body = update_response.json()
    assert update_response.status_code == 422
    assert res_body["resourceType"] == "OperationOutcome"

    # DELETE BOTH IMMUNIZATIONS
    delete_imms_response = imms_api.delete_immunization(parse_location(imms_response.headers["Location"]))
    assert delete_imms_response.status_code == 204
    delete_imms_2_response = imms_api.delete_immunization(parse_location(imms_2_response.headers["Location"]))
    assert delete_imms_2_response.status_code == 204


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
    json_data = result.json()

    assert result.status_code == 400
    assert json_data["resourceType"] == "OperationOutcome"
    assert path_id in json_data["issue"][0]["diagnostics"]


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
