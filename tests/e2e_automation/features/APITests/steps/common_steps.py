import copy
import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import pytest_check as check
from pytest_bdd import given, parsers, then, when
from src.dynamoDB.dynamo_db_helper import (
    fetch_immunization_events_detail,
    fetch_immunization_int_delta_detail_by_immsID,
    parse_imms_int_imms_event_response,
    validate_imms_delta_record_with_created_event,
)
from src.objectModels.api_immunization_builder import (
    build_site_route,
    build_vaccine_procedure_extension,
    convert_to_update,
    create_immunization_object,
    get_vaccine_details,
)
from src.objectModels.patient_loader import (
    get_gp_code_by_nhs_number,
    load_patient_by_id,
)
from utilities.api_fhir_immunization_helper import (
    get_response_body_for_display,
    is_valid_disease_type,
    is_valid_nhs_number,
    parse_error_response,
    validate_error_response,
    validate_to_compare_request_and_response,
)
from utilities.api_gen_token import get_tokens
from utilities.api_get_header import (
    get_create_post_url_header,
    get_delete_url_header,
    get_update_url_header,
)
from utilities.date_helper import is_valid_date, normalize_utc_suffix
from utilities.enums import ActionFlag, Operation
from utilities.http_requests_session import http_requests_session
from utilities.sqs_message_halder import read_message
from utilities.vaccination_constants import ROUTE_MAP, SITE_MAP


@given(parsers.parse("Valid token is generated for the '{Supplier}'"))
def valid_token_is_generated(context, Supplier):
    context.supplier_name = Supplier
    get_tokens(context, Supplier)


@given("Valid json payload is created")
def valid_json_payload_is_created(context):
    context.patient = load_patient_by_id(context.patient_id)
    context.immunization_object = create_immunization_object(context.patient, context.vaccine_type)


@given("Valid json payload is created where patient age is less then an year")
def valid_json_payload_is_created_patient_age_is_less_then_a_year(context):
    valid_json_payload_is_created(context)
    today = datetime.now(UTC)
    dob = today - timedelta(days=364)
    context.immunization_object.contained[1].birthDate = dob.strftime("%Y-%m-%d")


@given("Valid json payload is created where patient date is greater then vaccination occurrence date")
def valid_json_payload_is_created_patient_age_is_in_future(context):
    valid_json_payload_is_created(context)
    today = datetime.now(UTC)
    dob = today - timedelta(days=7)
    context.immunization_object.contained[1].birthDate = dob.strftime("%Y-%m-%d")
    occurrence_date = today - timedelta(days=14)
    context.immunization_object.occurrenceDateTime = occurrence_date.isoformat()


@given(parsers.parse("Valid json payload is created with Patient '{Patient}' and vaccine_type '{vaccine_type}'"))
def The_Immunization_object_is_created_with_patient_for_vaccine_type(context, Patient, vaccine_type):
    context.vaccine_type = vaccine_type
    context.patient_id = Patient
    context.patient = load_patient_by_id(context.patient_id)
    context.immunization_object = create_immunization_object(context.patient, context.vaccine_type)


@given(
    parsers.parse(
        "Valid json payload is created with Patient '{Patient}' and vaccine_type '{vaccine_type}' with minimal dataset"
    )
)
def The_Immunization_object_is_created_with_patient_for_vaccine_type_with_minimal_dataset(
    context, Patient, vaccine_type
):
    context.vaccine_type = vaccine_type
    context.patient_id = Patient
    context.patient = load_patient_by_id(context.patient_id)
    context.immunization_object = create_immunization_object(context.patient, context.vaccine_type)
    del context.immunization_object.lotNumber
    del context.immunization_object.manufacturer
    del context.immunization_object.expirationDate
    del context.immunization_object.site
    del context.immunization_object.route
    del context.immunization_object.reasonCode
    del context.immunization_object.doseQuantity


@given(parsers.parse("Valid vaccination record is created with Patient '{Patient}' and vaccine_type '{vaccine_type}'"))
def valid_vaccination_record_is_created_with_patient(context, Patient, vaccine_type):
    The_Immunization_object_is_created_with_patient_for_vaccine_type(context, Patient, vaccine_type)
    Trigger_the_post_create_request(context)
    The_request_will_have_status_code(context, 201)
    validateCreateLocation(context)
    mns_event_will_be_triggered_with_correct_data(context=context, action="CREATE")


@given(
    parsers.parse(
        "Valid vaccination record is created for '{NHSNumber}' and Disease Type '{vaccine_type}' with recorded date as '{DateFrom}'"
    )
)
def valid_vaccination_record_is_created_with_number_date(context, NHSNumber, vaccine_type, DateFrom):
    The_Immunization_object_is_created_with_patient_for_vaccine_type(context, "Random", vaccine_type)
    context.immunization_object.occurrenceDateTime = f"{DateFrom}T11:55:55.565+00:00"
    context.immunization_object.recorded = f"{DateFrom}T12:00:55.565+00:00"
    context.immunization_object.contained[1].identifier[0].value = NHSNumber
    Trigger_the_post_create_request(context)
    The_request_will_have_status_code(context, 201)
    validateCreateLocation(context)
    mns_event_will_be_triggered_with_correct_data(context=context, action="CREATE")


@given("I have created a valid vaccination record")
def validVaccinationRecordIsCreated(context):
    valid_json_payload_is_created(context)
    Trigger_the_post_create_request(context)
    The_request_will_have_status_code(context, 201)
    validateCreateLocation(context)
    if context.patient.identifier[0].value is not None:
        mns_event_will_be_triggered_with_correct_data(context=context, action="CREATE")
    else:
        mns_event_will_not_be_triggered_for_the_event(context)


@given(parsers.parse("valid vaccination record is created by '{Supplier}' supplier"))
def valid_vaccination_record_is_created_by_supplier(context, Supplier):
    valid_token_is_generated(context, Supplier)
    validVaccinationRecordIsCreated(context)


@when("Trigger the post create request")
def Trigger_the_post_create_request(context):
    get_create_post_url_header(context)
    context.create_object = context.immunization_object
    context.request = context.create_object.dict(exclude_none=True, exclude_unset=True)
    context.response = http_requests_session.post(context.url, json=context.request, headers=context.headers)
    print(f"Create Request is {json.dumps(context.request)}")


@then(parsers.parse("The request will be unsuccessful with the status code '{statusCode}'"))
@then(parsers.parse("The request will be successful with the status code '{statusCode}'"))
def The_request_will_have_status_code(context, statusCode):
    print(context.response.status_code)
    print(int(statusCode))
    body = get_response_body_for_display(context.response)
    assert context.response.status_code == int(statusCode), (
        f"\n Expected status code: {statusCode}, but got: {context.response.status_code}. Response: {body} \n"
    )


@then("The location key and Etag in header will contain the Immunization Id and version")
def validateCreateLocation(context):
    location = context.response.headers["location"]
    eTag = context.response.headers["E-Tag"]
    body = get_response_body_for_display(context.response)
    assert "location" in context.response.headers, (
        f"Location header is missing in the response with Status code: {context.response.status_code}. Response: {body}"
    )
    assert "E-Tag" in context.response.headers, (
        f"E-Tag header is missing in the response with Status code: {context.response.status_code}. Response: {body}"
    )
    context.ImmsID = location.split("/")[-1]
    context.eTag = eTag.strip('"')
    print(f"\n Immunization ID is {context.ImmsID} and Etag is {context.eTag} \n")
    check.is_true(
        context.ImmsID is not None,
        f"Expected IdentifierPK: {context.patient.identifier[0].value}, Found: {context.ImmsID}",
    )


@then("The Search Response JSONs should contain correct error message for invalid NHS Number")
@then("The Search Response JSONs should contain correct error message for invalid Disease Type")
@then("The Search Response JSONs should contain correct error message for invalid Date From")
@then("The Search Response JSONs should contain correct error message for invalid Date To")
@then("The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority")
@then("The Search Response JSONs should contain correct error message for invalid include")
@then("The Search Response JSONs should contain correct error message for invalid Date From and Date To")
@then("The Search Response JSONs should contain correct error message for invalid Date From, Date To and include")
def operationOutcomeInvalidParams(context):
    error_response = parse_error_response(context.response.json())
    params = getattr(context, "params", getattr(context, "request", {}))

    if isinstance(params, str):
        parsed = parse_qs(params)
        params = {k: v[0] for k, v in parsed.items()} if parsed else {}

    date_from_value = params.get("-date.from")
    date_to_value = params.get("-date.to")
    include_value = params.get("_include")
    nhs_number = params.get("patient.identifier").replace("https://fhir.nhs.uk/Id/nhs-number|", "")
    disease_type = params.get("-immunization.target")

    # Validation flags
    nhs_invalid = not is_valid_nhs_number(nhs_number)
    disease_invalid = not is_valid_disease_type(disease_type)
    date_from_invalid = date_from_value and not is_valid_date(date_from_value)
    date_to_invalid = date_to_value and not is_valid_date(date_to_value)
    include_invalid = include_value != "Immunization:patient"

    match (
        nhs_invalid,
        disease_invalid,
        date_from_invalid,
        date_to_invalid,
        include_invalid,
    ):
        case (True, _, _, _, _):
            expected_error = "invalid_NHSNumber"
        case (False, True, _, _, _):
            expected_error = "invalid_DiseaseType"
        case (False, False, True, True, False):
            expected_error = "invalid_DateFrom_To"
        case (False, False, True, True, True):
            expected_error = "invalid_DateFrom_DateTo_Include"
        case (False, False, True, _, True):
            expected_error = "invalid_DateFrom_Include"
        case (False, False, True, _, _):
            expected_error = "invalid_DateFrom"
        case (False, False, _, True, _):
            expected_error = "invalid_DateTo"
        case (False, False, _, _, True):
            expected_error = "invalid_include"
        case _:
            raise ValueError("All parameters are valid, no error expected.")

    validate_error_response(error_response, expected_error)
    print(f"\n Error Response - \n {error_response}")


@then("The X-Request-ID and X-Correlation-ID keys in header will populate correctly")
def validateCreateHeader(context):
    assert "X-Request-ID" in context.response.request.headers, "X-Request-ID missing in headers"
    assert "X-Correlation-ID" in context.response.request.headers, "X-Correlation-ID missing in headers"
    assert context.response.request.headers["X-Request-ID"] == context.reqID, "X-Request-ID incorrect"
    assert context.response.request.headers["X-Correlation-ID"] == context.corrID, "X-Correlation-ID incorrect"


@then(parsers.parse("The imms event table will be populated with the correct data for '{operation}' event"))
def validate_imms_event_table_by_operation(context, operation: Operation, reinstated=False):
    create_obj = context.create_object
    table_query_response = fetch_immunization_events_detail(context.aws_profile_name, context.ImmsID, context.S3_env)
    assert "Item" in table_query_response, f"Item not found in response for ImmsID: {context.ImmsID}"
    item = table_query_response["Item"]

    resource_json_str = item.get("Resource")
    assert resource_json_str, "Resource field missing in item."

    try:
        resource = json.loads(resource_json_str)
    except (TypeError, json.JSONDecodeError):
        raise AssertionError("Failed to parse Resource from response item.")

    assert resource is not None, "Resource is None in the response"
    created_event = parse_imms_int_imms_event_response(resource)

    assert int(context.expected_version) == int(context.eTag), (
        f"Expected Version: {context.expected_version}, Found: {context.eTag}"
    )
    actualDeletedAt = item.get("DeletedAt")
    fields_to_compare = [
        ("Operation", Operation[operation].value, item.get("Operation")),
        (
            "SupplierSystem",
            context.supplier_name.upper(),
            item.get("SupplierSystem").upper(),
        ),
        (
            "PatientPK",
            f"Patient#{context.patient.identifier[0].value if context.patient.identifier[0].value is not None else 'TBC'}",
            item.get("PatientPK"),
        ),
        (
            "PatientSK",
            f"{context.vaccine_type.upper()}#{context.ImmsID}",
            item.get("PatientSK"),
        ),
        ("Version", int(context.expected_version), int(item.get("Version"))),
    ]

    for name, expected, actual in fields_to_compare:
        check.is_true(expected == actual, f"Expected {name}: {expected}, Actual {actual}")

    if Operation[operation].value == "DELETE":
        check.is_true(
            actualDeletedAt is not None and actualDeletedAt > 0,
            f"Expected DeletedAt to be a Unix timestamp, got {actualDeletedAt}",
        )
    elif reinstated:
        check.is_true(
            actualDeletedAt == "reinstated",
            f"Expected DeletedAt: None for reinstated record, got {actualDeletedAt}",
        )
    else:
        check.is_true(
            actualDeletedAt is None,
            f"Expected DeletedAt: None, Actual {actualDeletedAt}",
        )

    validate_to_compare_request_and_response(context, create_obj, created_event, True)


@then(parsers.parse("The Response JSONs should contain correct error message for '{errorName}'"))
@then(parsers.parse("The Response JSONs should contain correct error message for '{errorName}' access"))
@then(parsers.parse("The Response JSONs should contain correct error message for Imms_id '{errorName}'"))
def validateForbiddenAccess(context, errorName):
    error_response = parse_error_response(context.response.json())
    if errorName == "duplicate":
        identifier = (
            f"{context.immunization_object.identifier[0].system}#{context.immunization_object.identifier[0].value}"
        )
        validate_error_response(error_response, errorName, identifier=identifier)
    else:
        validate_error_response(error_response, errorName, imms_id=context.ImmsID)
    print(f"\n Error Response - \n {error_response}")


@then("The Etag in header will containing the latest event version")
def validate_etag_in_header(context):
    etag = context.response.headers["E-Tag"]
    assert etag, "Etag header is missing in the response"
    context.eTag = etag.strip('"')
    assert context.eTag == str(context.expected_version), (
        f"Etag version mismatch: expected {context.expected_version}, got {context.eTag}"
    )


@when("I subsequently update the vaccination details of the original immunization event")
def send_update_for_vaccination_detail(context):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.extension = [build_vaccine_procedure_extension(context.vaccine_type.upper())]
    vaccine_details = get_vaccine_details(context.vaccine_type.upper())
    context.update_object.vaccineCode = vaccine_details["vaccine_code"]
    context.update_object.site = build_site_route(random.choice(SITE_MAP))
    context.update_object.route = build_site_route(random.choice(ROUTE_MAP))
    trigger_the_updated_request(context)


@when("I update the address of the original immunization event")
def send_update_for_immunization_event(context):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.contained[1].address[0].city = "Updated City"
    context.update_object.contained[1].address[0].state = "Updated State"
    trigger_the_updated_request(context)


@given("created event is being updated twice")
def created_event_is_being_updated_twice(context):
    send_update_for_immunization_event(context)
    The_request_will_have_status_code(context, 200)
    mns_event_will_be_triggered_with_correct_data(context=context, action="UPDATE")
    send_update_for_vaccination_detail(context)
    The_request_will_have_status_code(context, 200)
    mns_event_will_be_triggered_with_correct_data(context=context, action="UPDATE")


@given("created event is being deleted")
def created_event_is_being_deleted(context):
    send_delete_for_immunization_event_created(context)
    The_request_will_have_status_code(context, 204)


@when("same delete request is triggered again")
@when("Send a delete for Immunization event created")
def send_delete_for_immunization_event_created(context):
    get_delete_url_header(context)
    print(f"\n Delete Request is {context.url}/{context.ImmsID}")
    context.response = http_requests_session.delete(f"{context.url}/{context.ImmsID}", headers=context.headers)


@then("MNS event will be triggered with correct data for created event")
def mns_event_will_be_triggered_with_correct_data_for_created_event(context):
    mns_event_will_be_triggered_with_correct_data(context=context, action="CREATE")


@then("MNS event will not be triggered for the event")
def mns_event_will_not_be_triggered_for_the_event(context):
    if context.mns_validation_required.strip().lower() == "true":
        message_body = read_message(
            context,
            queue_type="notification",
            wait_time_seconds=5,
            max_total_wait_seconds=20,
        )
        print("No MNS create event is created")
        assert message_body is None, "Not expected a message but queue returned a message"
    else:
        print(
            f"MNS event validation is skipped since mns_validation_required is set to {context.mns_validation_required}"
        )


@then("MNS event will not be triggered for the update event")
def validate_mns_event_not_triggered_for_updated_event(context):
    mns_event_will_not_be_triggered_for_the_event(context)


@when("Trigger another post create request with same unique_id and unique_id_uri")
def trigger_post_create_with_same_unique_id(context):
    context.immunization_object.contained[1].address[0].city = "Updated City"
    context.immunization_object.contained[1].address[0].state = "Updated State"
    Trigger_the_post_create_request(context)


@then("The delta table will be populated with the correct data for updated event")
def validate_delta_table_for_updated_event(context):
    create_obj = context.create_object
    items = fetch_immunization_int_delta_detail_by_immsID(
        context.aws_profile_name,
        context.ImmsID,
        context.S3_env,
        context.expected_version,
    )
    assert items, f"Items not found in response for ImmsID: {context.ImmsID}"
    delta_items = [i for i in items if i.get("Operation") == Operation.updated.value]
    assert delta_items, f"No item found for ImmsID: {context.ImmsID}"
    latest_delta_record = max(delta_items, key=lambda x: x.get("SequenceNumber", -1))
    validate_imms_delta_record_with_created_event(
        context,
        create_obj,
        latest_delta_record,
        Operation.updated.value,
        ActionFlag.updated.value,
    )


@then("MNS event will be triggered with correct data for Updated event")
def validate_mns_event_triggered_for_updated_event(context):
    mns_event_will_be_triggered_with_correct_data(context=context, action="UPDATE")


def trigger_the_updated_request(context):
    context.expected_version = int(context.expected_version) + 1
    context.create_object = context.update_object
    context.request = context.update_object.dict(exclude_none=True, exclude_unset=True)
    context.response = http_requests_session.put(
        context.url + "/" + context.ImmsID,
        json=context.request,
        headers=context.headers,
    )
    print(f"Update Request is {json.dumps(context.request)}")


def normalize_param(value: str) -> str:
    return "" if value.lower() in {"none", "null", ""} else value


def calculate_age(birth_date_str: str, occurrence_datetime_str: str) -> int:
    birth = parse_birth_date(birth_date_str)
    occurrence = datetime.fromisoformat(occurrence_datetime_str).date()
    age = occurrence.year - birth.year
    if (occurrence.month, occurrence.day) < (birth.month, birth.day):
        age -= 1
    return age


def parse_birth_date(date_str: str) -> datetime.date:
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid birth date format: {date_str}")


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def normalize(value: str) -> str:
    return value.strip().upper() if value else ""


def validate_sqs_message(context, message_body, action):
    check.is_true(message_body.specversion == "1.0")
    check.is_true(message_body.source == "uk.nhs.vaccinations-data-flow-management")
    check.is_true(message_body.type == "imms-vaccination-record-change-1")

    check.is_true(is_valid_uuid(message_body.id), f"Invalid UUID: {message_body.id}")

    imms_date_time = normalize_utc_suffix(context.immunization_object.occurrenceDateTime)
    check.is_true(
        message_body.time == imms_date_time,
        f"msn event for {action} Time missing or mismatch: message_body.time = {message_body.time}, imms_date_time = {imms_date_time}",
    )
    expected_nhs_number = context.patient.identifier[0].value
    if expected_nhs_number is None:
        expected_nhs_number = ""
    check.is_true(
        message_body.subject == expected_nhs_number,
        f"msn event for {action}Subject mismatch: expected {expected_nhs_number}, got {message_body.subject}",
    )

    check.is_true(
        message_body.dataref == f"{context.url}/{context.ImmsID}",
        f"msn event for {action} DataRef mismatch: expected {context.url}/{context.ImmsID}, got {message_body.dataref}",
    )

    if context.S3_env not in ["int", "preprod"]:
        check.is_true(
            message_body.filtering is not None,
            f"msn event for {action} Filtering is missing in the message body",
        )

        if context.gp_code:
            check.is_true(
                normalize(message_body.filtering.generalpractitioner) == normalize(context.gp_code),
                f"msn event for {action} GP code mismatch: expected {context.gp_code}, got {message_body.filtering.generalpractitioner}",
            )

        expected_org = context.immunization_object.performer[1].actor.identifier.value
        check.is_true(
            normalize(message_body.filtering.sourceorganisation) == normalize(expected_org),
            f"msn event for {action} Source org mismatch: expected {expected_org}, got {message_body.filtering.sourceorganisation}",
        )

        check.is_true(
            message_body.filtering.sourceapplication.upper() == context.supplier_name.upper(),
            f"msn event for {action} Source application mismatch: expected {context.supplier_name}, got {message_body.filtering.sourceapplication}",
        )

        if context.patient_age:
            check.is_true(
                message_body.filtering.subjectage == context.patient_age,
                f"msn event for {action} Age mismatch: expected {context.patient_age}, got {message_body.filtering.subjectage}",
            )

        check.is_true(
            message_body.filtering.immunisationtype == context.vaccine_type.upper(),
            f"msn event for {action} Immunisation type mismatch: expected {context.vaccine_type.upper()}, got {message_body.filtering.immunisationtype}",
        )

        check.is_true(
            message_body.filtering.action == action.upper(),
            f"msn event for {action} Action mismatch: expected {action.upper()}, got {message_body.filtering.action}",
        )
    else:
        check.is_true(
            message_body.filtering is None,
            f"msn event for {action} Filtering is present in the message body when it shouldn't be for int environment",
        )


def mns_event_will_be_triggered_with_correct_data_for_deleted_event(context):
    if context.mns_validation_required.strip().lower() == "true":
        if context.patient.identifier[0].value is None:
            message_body = read_message(
                context,
                queue_type="notification",
                wait_time_seconds=5,
                max_total_wait_seconds=20,
            )
            print(
                "No MNS delete event is created as expected since NHS number is not present in the original immunization event"
            )
            assert message_body is None, "Not expected a message but queue returned a message"
        else:
            message_body = read_message(context, queue_type="notification")
            print(f"Read deleted message from SQS: {message_body}")
            assert message_body is not None, "Expected a  delete message but queue returned empty"
            validate_sqs_message(context, message_body, "DELETE")
    else:
        print("MNS validation not required, skipping MNS event verification for deleted event.")


def mns_event_will_be_triggered_with_correct_data(context, action):
    if context.mns_validation_required.strip().lower() == "true":
        message_body = read_message(context, queue_type="notification")
        print(f"Read {action}d message from SQS: {message_body}")
        assert message_body is not None, f"Expected a {action} message but queue returned empty"
        context.gp_code = get_gp_code_by_nhs_number(context.patient.identifier[0].value)
        patient_DOB = (
            context.immunization_object.contained[1].birthDate
            if action.upper() == "CREATE"
            else context.update_object.contained[1].birthDate
        )
        context.patient_age = calculate_age(patient_DOB, context.immunization_object.occurrenceDateTime)
        validate_sqs_message(context, message_body, action)
    else:
        print(
            f"MNS event validation is skipped since mns_validation_required is set to {context.mns_validation_required}"
        )


def trigger_update_request_with_same_unique_id_and_uri_for_deleted_record(context):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    trigger_the_updated_request(context)
