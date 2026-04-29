import logging
import uuid

from pytest_bdd import parsers, scenarios, then, when
from pytest_check.context_manager import check
from src.dynamoDB.dynamo_db_helper import (
    fetch_immunization_int_delta_detail_by_immsID,
    validate_imms_delta_record_with_created_event,
)
from utilities.api_fhir_immunization_helper import (
    find_entry_by_Imms_id,
    parse_FHIR_immunization_response,
)
from utilities.api_get_header import get_delete_url_header
from utilities.enums import ActionFlag, Operation
from utilities.http_requests_session import http_requests_session

from .common_steps import (
    The_request_will_have_status_code,
    send_delete_for_immunization_event_created,
    valid_token_is_generated,
)
from .test_search_steps import trigger_search_request

logging.basicConfig(filename="debugLog.log", level=logging.INFO)
logger = logging.getLogger(__name__)


scenarios("APITests/delete.feature")


@when("Send a delete for Immunization event created with invalid Imms Id")
def send_delete_for_immunization_event_created_invalid(context):
    get_delete_url_header(context)
    context.ImmsID = str(uuid.uuid4())
    print(f"\n Delete Request is {context.url}/{context.ImmsID}")
    context.response = http_requests_session.delete(f"{context.url}/{context.ImmsID}", headers=context.headers)


@when(parsers.parse("Send a delete for Immunization event created for the above created event is send by '{Supplier}'"))
def send_delete_for_immunization_event_by_supplier(context, Supplier):
    valid_token_is_generated(context, Supplier)
    send_delete_for_immunization_event_created(context)


@then("The delta table will be populated with the correct data for deleted event")
def validate_imms_delta_table_by_deleted_ImmsID(context):
    create_obj = context.create_object
    items = fetch_immunization_int_delta_detail_by_immsID(context.aws_profile_name, context.ImmsID, context.S3_env, 2)
    assert items, f"Items not found in response for ImmsID: {context.ImmsID}"

    # Find the latest item where operation is DELETE
    deleted_items = [i for i in items if i.get("Operation") == Operation.deleted.value]
    assert deleted_items, f"No deleted item found for ImmsID: {context.ImmsID}"

    # Assuming each item has a 'timestamp' field to determine the latest
    latest_delta_record = max(deleted_items, key=lambda x: x.get("timestamp", 0))

    validate_imms_delta_record_with_created_event(
        context,
        create_obj,
        latest_delta_record,
        Operation.deleted.value,
        ActionFlag.deleted.value,
    )


@then("Deleted Immunization event will not be present in Get method Search API response")
def validate_deleted_immunization_event_not_present(context):
    trigger_search_request(context, httpMethod="GET")
    The_request_will_have_status_code(context, "200")

    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)

    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)

    assert context.created_event is None, (
        f"Immunization event with ID {context.ImmsID} should not be present in the search response after deletion."
    )


@then("Deleted Immunization event will not be present in Post method Search API response")
def validate_deleted_immunization_event_not_present_using_post(context):
    trigger_search_request(context, httpMethod="POST")
    The_request_will_have_status_code(context, "200")

    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)

    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)

    assert context.created_event is None, (
        f"Immunization event with ID {context.ImmsID} should not be present in the search response after deletion."
    )


@then(
    "The location key and Etag in header will contain the  previous Immunization Id and version will be incremented by 1"
)
def validate_location_key_and_etag_in_header(context):
    location = context.response.headers["location"]
    eTag = context.response.headers["E-Tag"]
    context.expected_version += 1
    assert "location" in context.response.headers, (
        f"Location header is missing in the response with Status code: {context.response.status_code}. Response: {context.response.text}"
    )
    assert "E-Tag" in context.response.headers, (
        f"E-Tag header is missing in the response with Status code: {context.response.status_code}. Response: {context.response.text}"
    )
    print(f"\n Immunization ID is {context.ImmsID} and Etag is {context.eTag} \n")
    check.is_true(
        context.ImmsID == location.split("/")[-2],
        f"Expected imms id sholud be : {context.ImmsID}, Found: {location}",
    )
    check.is_true(
        str(context.expected_version) == eTag.strip('"'),
        f"Expected version should be : {context.expected_version}, Found: {eTag}",
    )


@then("MNS event will be triggered with correct data for Deleted event")
def mns_event_will_be_triggered_with_correct_data_for_deleted_event(context):
    mns_event_will_be_triggered_with_correct_data_for_deleted_event(context)
