import logging
import uuid

from pytest_bdd import scenarios, then, when
from utilities.api_fhir_immunization_helper import (
    parse_read_response,
    validate_to_compare_request_and_response,
)
from utilities.api_get_header import get_read_url_header
from utilities.http_requests_session import http_requests_session

logging.basicConfig(filename="debugLog.log", level=logging.INFO)
logger = logging.getLogger(__name__)

scenarios("APITests/read.feature")


@when("Send a read request for Immunization event created")
def send_read_for_immunization_event_created(context):
    get_read_url_header(context)
    print(f"\n Read Request is {context.url}")
    context.response = http_requests_session.get(
        f"{context.url}", headers=context.headers
    )


@then(
    "The Read Response JSONs field values should match with the input JSONs field values"
)
def the_read_response_jsons_field_values_should_match_with_the_input_jsons_field_values(
    context,
):
    create_obj = context.create_object
    data = context.response.json()
    context.created_event = parse_read_response(data)
    validate_to_compare_request_and_response(
        context, create_obj, context.created_event, True
    )


@when("Send a read request for Immunization event created with invalid Imms Id")
def send_read_for_immunization_event_created_with_invalid_imms_id(context):
    context.ImmsID = str(uuid.uuid4())
    get_read_url_header(context)
    print(f"\n Read Request is {context.url}")
    context.response = http_requests_session.get(
        f"{context.url}", headers=context.headers
    )


@when("Send a read request with no Imms Id")
def send_read_for_immunization_event_created_with_no_imms_id(context):
    context.ImmsID = " "
    get_read_url_header(context)
    print(f"\n Read Request is {context.url}")
    context.response = http_requests_session.get(
        f"{context.url}", headers=context.headers
    )
