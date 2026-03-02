import uuid
from datetime import datetime
from urllib.parse import parse_qs

import pytest_check as check
from pytest_bdd import parsers, scenarios, then, when
from src.objectModels.api_search_object import convert_to_form_data, set_request_data
from utilities.api_fhir_immunization_helper import (
    find_entry_by_Imms_id,
    find_patient_by_fullurl,
    parse_error_response,
    parse_FHIR_immunization_response,
    validate_error_response,
    validate_to_compare_request_and_response,
)
from utilities.api_get_header import get_search_get_url_header, get_search_post_url_header
from utilities.date_helper import iso_to_compact
from utilities.http_requests_session import http_requests_session

from .common_steps import normalize_param

scenarios("APITests/search.feature")

TARGET_DISEASE_SYSTEM = "http://snomed.info/sct"
TARGET_DISEASE_MEASLES_CODE = "14189004"
TARGET_DISEASE_MUMPS_CODE = "36989005"
PATIENT_IDENTIFIER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"


@when("I send a search request with Post method using identifier parameter for Immunization event created")
def send_search_post_request_with_identifier_header(context):
    context.request = {
        "identifier": f"{context.create_object.identifier[0].system}|{context.create_object.identifier[0].value}"
    }
    trigger_search_request_by_httpMethod(context, httpMethod="POST")


@when(
    "I send a search request with Post method using identifier and _elements parameters for Immunization event created"
)
def send_search_post_request_with_identifier_and_elements_header(context):
    context.request = {
        "identifier": f"{context.create_object.identifier[0].system}|{context.create_object.identifier[0].value}",
        "_elements": "meta,id",
    }
    trigger_search_request_by_httpMethod(context, httpMethod="POST")


@when("I send a search request with Post method using an invalid identifier header for Immunization event created")
def send_search_post_request_with_invalid_identifier_header(context):
    context.request = {
        "identifier": f"https://www.ieds.england.nhs.uk/|{str(uuid.uuid4())}",
        "_elements": "meta,id",
    }
    trigger_search_request_by_httpMethod(context, httpMethod="POST")


@when(parsers.parse("Send a search request with '{httpMethod}' method for Immunization event created"))
def trigger_search_request(context, httpMethod):
    context.params = context.request = convert_to_form_data(
        set_request_data(
            context.patient.identifier[0].value,
            context.vaccine_type,
            datetime.today().strftime("%Y-%m-%d"),
        )
    )
    trigger_search_request_by_httpMethod(context, httpMethod=httpMethod)


@when("Send a search request with GET method using target-disease for Immunization event created")
def send_search_get_with_target_disease(context):
    get_search_get_url_header(context)
    nhs_number = context.patient.identifier[0].value
    context.params = {
        "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
    }
    print(f"\n Search Get parameters (target-disease) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when("Send a search request with POST method for Immunization event created")
def TriggerSearchPostRequest(context):
    get_search_post_url_header(context)
    context.request = convert_to_form_data(
        set_request_data(
            context.patient.identifier[0].value, context.vaccine_type, datetime.today().strftime("%Y-%m-%d")
        )
    )
    print(f"\n Search Post Request - \n {context.request}")
    context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)
    print(f"\n Search Post Response - \n {context.response.json()}")


@when("Send a search request with POST method using target-disease for Immunization event created")
def send_search_post_with_target_disease(context):
    get_search_post_url_header(context)
    nhs_number = context.patient.identifier[0].value
    context.request = {
        "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
    }
    print(f"\n Search Post request (target-disease) - \n {context.request}")
    context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)


@when("Send a search request with GET method using comma-separated target-disease for Immunization event created")
def send_search_get_with_comma_separated_target_disease(context):
    get_search_get_url_header(context)
    nhs_number = context.patient.identifier[0].value
    context.params = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE},{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MUMPS_CODE}",
    }
    print(f"\n Search Get parameters (comma-separated target-disease) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when("Send a search request with POST method using comma-separated target-disease for Immunization event created")
def send_search_post_with_comma_separated_target_disease(context):
    get_search_post_url_header(context)
    nhs_number = context.patient.identifier[0].value
    context.request = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE},{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MUMPS_CODE}",
    }
    print(f"\n Search Post request (comma-separated target-disease) - \n {context.request}")
    context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)


@when(
    "Send a search request with GET method using target-disease and Date From and Date To for Immunization event created"
)
def send_search_get_with_target_disease_and_dates(context):
    get_search_get_url_header(context)
    nhs_number = "9728403348"
    context.DateFrom = "2023-01-01"
    context.DateTo = "2023-06-04"
    context.params = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
        "-date.from": context.DateFrom,
        "-date.to": context.DateTo,
    }
    print(f"\n Search Get parameters (target-disease with dates) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when(
    "Send a search request with POST method using target-disease and Date From and Date To for Immunization event created"
)
def send_search_post_with_target_disease_and_dates(context):
    get_search_post_url_header(context)
    nhs_number = "9728403348"
    context.DateFrom = "2023-01-01"
    context.DateTo = "2023-06-04"
    context.request = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
        "-date.from": context.DateFrom,
        "-date.to": context.DateTo,
    }
    print(f"\n Search Post request (target-disease with dates) - \n {context.request}")
    context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)


@when("Send a search request with GET method using target-disease for Immunization event created with valid NHS Number")
def send_search_get_with_target_disease_unauthorised_supplier(context):
    get_search_get_url_header(context)
    nhs_number = "9000000009"
    context.params = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
    }
    print(f"\n Search Get parameters (target-disease, 403 check) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when("Send a search request with GET method with valid NHS Number and all invalid target-disease codes")
def send_search_get_with_all_invalid_target_disease_codes(context):
    get_search_get_url_header(context)
    context.params = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|9000000009",
        "target-disease": "invalid-no-pipe,wrong_system|123",
    }
    print(f"\n Search Get parameters (all invalid target-disease) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when("Send a search request with POST method with valid NHS Number and all invalid target-disease codes")
def send_search_post_with_all_invalid_target_disease_codes(context):
    get_search_post_url_header(context)
    context.request = {
        "patient.identifier": f"{PATIENT_IDENTIFIER_SYSTEM}|9000000009",
        "target-disease": "invalid-no-pipe,wrong_system|123",
    }
    print(f"\n Search Post request (all invalid target-disease) - \n {context.request}")
    context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid NHS Number and mixed valid and invalid Disease Type"
    )
)
def send_search_request_with_mixed_targets(context, httpMethod):
    mixed_target = f"{context.vaccine_type},INVALID_TYPE"
    context.params = context.request = convert_to_form_data(
        set_request_data(
            context.patient.identifier[0].value,
            mixed_target,
            datetime.today().strftime("%Y-%m-%d"),
        )
    )
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(parsers.parse("Send a search request with '{httpMethod}' method with valid NHS Number and multiple Disease Type"))
def send_search_post_with_mixed_valid_unauthorized_targets(context, httpMethod):
    mixed_target = f"{context.vaccine_type},6IN1"
    context.params = context.request = convert_to_form_data(
        set_request_data(
            context.patient.identifier[0].value,
            mixed_target,
            datetime.today().strftime("%Y-%m-%d"),
        )
    )
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(
    "Send a search request with GET method using target-disease and -immunization.target for Immunization event created"
)
def send_search_get_with_target_disease_and_immunization_target(context):
    get_search_get_url_header(context)
    nhs_number = "9000000009"
    context.params = {
        "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
        "-immunization.target": "MMR",
    }
    print(f"\n Search Get parameters (target-disease with -immunization.target) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when("Send a search request with GET method using target-disease and identifier for Immunization event created")
def send_search_get_with_target_disease_and_identifier(context):
    get_search_get_url_header(context)
    nhs_number = "9000000009"
    context.params = {
        "patient.identifier": f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
        "target-disease": f"{TARGET_DISEASE_SYSTEM}|{TARGET_DISEASE_MEASLES_CODE}",
        "identifier": "https://example.org|abc-123",
    }
    print(f"\n Search Get parameters (target-disease with identifier) - \n {context.params}")
    context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with invalid NHS Number '{NHSNumber}' and valid Disease Type '{DiseaseType}'"
    )
)
@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"
    )
)
@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with invalid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"
    )
)
def send_invalid_param_get_request(context, httpMethod, NHSNumber, DiseaseType):
    NHSNumber = normalize_param(NHSNumber)
    DiseaseType = normalize_param(DiseaseType)
    context.params = context.request = convert_to_form_data(
        set_request_data(NHSNumber, DiseaseType, datetime.today().strftime("%Y-%m-%d"))
    )
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with invalid Date From '{DateFrom}' and valid Date To '{DateTo}'"
    )
)
@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid Date From '{DateFrom}' and invalid Date To '{DateTo}'"
    )
)
@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with invalid Date From '{DateFrom}' and invalid Date To '{DateTo}'"
    )
)
def send_invalid_date_get_request(context, httpMethod, DateFrom, DateTo):
    context.params = context.request = convert_to_form_data(
        set_request_data(9001066569, context.vaccine_type, DateFrom, DateTo)
    )
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid NHS Number '{NHSNumber}' and Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}'"
    )
)
def send_valid_param_get_request(context, httpMethod, NHSNumber, vaccine_type, DateFrom, DateTo):
    context.params = context.request = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo))
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and invalid include '{include}'"
    )
)
def send_valid_param_get_request_with_include(context, httpMethod, NHSNumber, vaccine_type, include):
    context.params = context.request = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, include=include))
    trigger_search_request_by_httpMethod(context, httpMethod)


@when(
    parsers.parse(
        "Send a search request with '{httpMethod}' method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}' and include '{include}'"
    )
)
def send_valid_param_get_request_with_include_and_dates(
    context, httpMethod, NHSNumber, vaccine_type, DateFrom, DateTo, include
):
    context.params = context.request = convert_to_form_data(
        set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo, include)
    )
    trigger_search_request_by_httpMethod(context, httpMethod)


@then("The occurrenceDateTime of the immunization events should be within the Date From and Date To range")
def validate_date_range(context):
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)
    params = getattr(context, "params", getattr(context, "request", {}))
    if isinstance(params, str):
        parsed = parse_qs(params)
        params = {k: v[0] for k, v in parsed.items()} if parsed else {}
    dateFrom = params.get("-date.from")
    dateTo = params.get("-date.to")
    assert context.parsed_search_object.entry, "No entries found in the search response."
    for entry in context.parsed_search_object.entry:
        if entry.resource.resourceType == "Immunization":
            occurrence_date = entry.resource.occurrenceDateTime
            id = entry.resource.id
            if occurrence_date:
                if dateFrom and dateTo:
                    occurrence_date = iso_to_compact(occurrence_date)
                    date_from = iso_to_compact(dateFrom)
                    date_to = iso_to_compact(dateTo)

                    assert date_from <= occurrence_date <= date_to, (
                        f"Occurrence date {occurrence_date} is not within the range Date From {context.DateFrom} and Date To {context.DateTo}. Imms ID: {id}"
                    )


@then("The Search Response JSONs should contain the detail of the immunization events created above")
def validate_imms_id(context):
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)
    assert context.parsed_search_object.resourceType == "Bundle", (
        f"expected resourceType to be 'Bundle' but got {context.parsed_search_object.resourceType}"
    )
    assert context.parsed_search_object.type == "searchset", (
        f"expected resourceType to be 'searchset' but got {context.parsed_search_object.type}"
    )
    assert context.parsed_search_object.link[0].relation == "self", (
        f"expected link relation to be 'self' but got {context.parsed_search_object.link[0].relation}"
    )
    assert context.parsed_search_object.link[0].url.startswith(context.baseUrl), (
        f"Expected link URL to start with '{context.baseUrl}', but got '{context.parsed_search_object.link[0].url}'"
    )
    assert context.parsed_search_object.total >= 1, (
        f"expected total to be greater than or equal to 1 but got {context.parsed_search_object.total}"
    )
    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)
    if context.created_event is None:
        raise AssertionError(f"No object found with Immunisation ID {context.ImmsID} in the search response.")
    patient_reference = getattr(context.created_event.resource.patient, "reference", None)
    if not patient_reference:
        raise ValueError("Patient reference is missing in the found event.")
    context.Patient_fullUrl = patient_reference


@then(
    "The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization"
)
def validate_json_imms(context):
    create_obj = context.create_object
    created_event = context.created_event.resource
    validate_to_compare_request_and_response(context, create_obj, created_event)


@then("The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient")
def validate_json_patient(context):
    response_patient_entry = find_patient_by_fullurl(context.parsed_search_object)
    assert response_patient_entry is not None, f"No Patient found with fullUrl {context.Patient_fullUrl}"
    response_patient = response_patient_entry.resource
    expected_nhs_number = context.create_object.contained[1].identifier[0].value
    actual_nhs_number = response_patient.identifier[0].value
    expected_system = context.create_object.contained[1].identifier[0].system
    actual_system = response_patient.identifier[0].system
    fields_to_compare = [
        ("fullUrl", context.Patient_fullUrl, response_patient_entry.fullUrl),
        ("resourceType", "Patient", response_patient.resourceType),
        ("id", expected_nhs_number, response_patient.id),
        ("identifier.system", expected_system, actual_system),
        ("identifier.value", expected_nhs_number, actual_nhs_number),
    ]
    for name, expected, actual in fields_to_compare:
        check.is_true(expected == actual, f"Expected {name}: {expected}, Actual {actual}")


@then("correct immunization event is returned in the response")
def validate_correct_immunization_event(context):
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)
    context.created_event = context.parsed_search_object.entry[0] if context.parsed_search_object.entry else None
    if context.created_event is None:
        raise AssertionError(f"No object found with Immunisation ID {context.ImmsID} in the search response.")
    validate_json_imms(context)
    assert context.parsed_search_object.resourceType == "Bundle", (
        f"expected resourceType to be 'Bundle' but got {context.parsed_search_object.resourceType}"
    )
    assert context.parsed_search_object.type == "searchset", (
        f"expected resourceType to be 'searchset' but got {context.parsed_search_object.type}"
    )
    assert context.parsed_search_object.link[0].relation == "self", (
        f"expected link relation to be 'self' but got {context.parsed_search_object.link[0].relation}"
    )
    assert context.parsed_search_object.link[0].url.startswith(context.baseUrl), (
        f"Expected link URL to start with '{context.baseUrl}', but got '{context.parsed_search_object.link[0].url}'"
    )
    assert context.parsed_search_object.total == 1, (
        f"expected total to be greater than or equal to 1 but got {context.parsed_search_object.total}"
    )


@then("correct immunization event is returned in the response with only specified elements")
def validate_correct_immunization_event_with_elements(context):
    response = context.response.json()
    assert response.get("resourceType") == "Bundle", "resourceType should be 'Bundle'"
    assert response.get("type") == "searchset", "type should be 'searchset'"
    assert isinstance(response.get("entry"), list) and len(response["entry"]) > 0, " entry list is missing or empty"
    link = response.get("link", [{}])[0]
    link_url = link.get("url")
    assert link_url is not None, " link[0].url is missing"
    assert link_url.startswith(context.baseUrl), f"link[0].url should start with '{context.baseUrl}', got '{link_url}'"
    resource = response["entry"][0].get("resource", {})
    assert resource.get("resourceType") == "Immunization", "resourceType should be 'Immunization'"
    assert "id" in resource, "resource.id is missing"
    assert "meta" in resource and "versionId" in resource["meta"], " meta.versionId is missing"
    assert resource["id"] == context.ImmsID, f"resource.id mismatch: expected '{context.ImmsID}', got '{resource['id']}'"
    assert str(resource["meta"]["versionId"]) == str(context.expected_version), (
        f"meta.versionId mismatch: expected '{context.expected_version}', got '{resource['meta']['versionId']}'"
    )
    assert response.get("total") == 1, "total should be 1"


@then("Empty immunization event is returned in the response")
def validate_empty_immunization_event(context):
    response = context.response.json()
    assert response.get("resourceType") == "Bundle", "resourceType should be 'Bundle'"
    assert response.get("type") == "searchset", "type should be 'searchset'"
    assert isinstance(response.get("entry"), list) and len(response["entry"]) == 0, " entry list should be empty"
    link = response.get("link", [{}])[0]
    link_url = link.get("url")
    assert link_url is not None, " link[0].url is missing"
    assert link_url == f"{context.baseUrl}/Immunization?identifier=None", (
        f"link[0].url should be '{context.baseUrl}/Immunization?identifier=None', got '{link_url}'"
    )
    assert response.get("total") == 0, "total should be 0"


@then("The Response JSONs should contain correct error message for invalid target-disease usage")
def validate_invalid_target_disease_usage_error(context):
    response = context.response.json()
    diagnostics = (response.get("issue") or [{}])[0].get("diagnostics", "")
    assert "cannot be used with" in diagnostics, (
        f"Expected diagnostics to mention mutual exclusivity, got: {diagnostics}"
    )
    assert "target-disease" in diagnostics, f"Expected diagnostics to mention target-disease, got: {diagnostics}"


@then("The Response JSONs should contain correct error message for invalid target-disease codes")
def validate_invalid_target_disease_codes_error(context):
    error_response = parse_error_response(context.response.json())
    validate_error_response(error_response, "invalid_target_disease_codes")
    print(f"\n Error Response (invalid target-disease codes) - \n {context.response.json()}")


@then("The Search Response should contain search results and OperationOutcome for invalid immunization targets")
def validate_search_response_with_invalid_targets_operation_outcome(context):
    issue = read_issue_from_response(context)
    expected_diagnostics = "Your search included invalid -immunization.target value(s) that were ignored: INVALID_TYPE. The search was performed using the valid value(s) only."
    validate_issue(issue, expected_code="invalid", expected_diag=expected_diagnostics)


@then("The Search Response should contain search results and OperationOutcome for unauthorized immunization targets")
def validate_search_response_with_unauthorized_targets_operation_outcome(context):
    issue = read_issue_from_response(context)
    expected_diagnostics = "Your search contains details that you are not authorised to request"
    validate_issue(issue, expected_code="unauthorized", expected_diag=expected_diagnostics)


def read_issue_from_response(context):
    response = context.response.json()
    assert response.get("resourceType") == "Bundle", "resourceType should be 'Bundle'"
    assert response.get("type") == "searchset", "type should be 'searchset'"

    entries = response.get("entry", [])
    assert len(entries) >= 1, "Bundle should contain at least one entry"

    imms_entry = next(
        (
            e
            for e in entries
            if e.get("resource", {}).get("resourceType") == "Immunization"
            and e.get("resource", {}).get("id") == context.ImmsID
        ),
        None,
    )
    assert imms_entry is not None, f"Expected Immunization entry with id {context.ImmsID} in search response"

    oo_entries = [e for e in entries if e.get("resource", {}).get("resourceType") == "OperationOutcome"]
    assert len(oo_entries) >= 1, "Bundle should contain at least one OperationOutcome entry"

    issue = oo_entries[0].get("resource", {}).get("issue", [{}])[0]

    assert issue is not None, "OperationOutcome issue is missing"

    return issue


def validate_issue(issue, expected_code, expected_diag):
    assert issue.get("severity") == "warning", "issue severity should be 'warning'"
    assert issue.get("code") == expected_code, f"issue code should be '{expected_code}'"
    assert issue.get("diagnostics") == expected_diag, f"issue diagnostics should be '{expected_diag}'"


def trigger_search_request_by_httpMethod(context, httpMethod="GET"):
    if httpMethod == "POST":
        get_search_post_url_header(context)
        print(f"\n Search Post Request - \n {context.request}")
        context.response = http_requests_session.post(context.url, headers=context.headers, data=context.request)

    else:
        get_search_get_url_header(context)
        print(f"\n Search {httpMethod} Request - \n {context.params}")
        context.response = http_requests_session.get(context.url, params=context.params, headers=context.headers)
    print(f"\n Search {httpMethod} Response - \n {context.response.json()}")
