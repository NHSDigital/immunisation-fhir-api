import copy
import uuid

from pytest_bdd import parsers, scenarios, then, when
from src.objectModels.api_immunization_builder import convert_to_update
from utilities.api_fhir_immunization_helper import (
    parse_error_response,
    validate_error_response,
)
from utilities.api_get_header import get_update_url_header
from utilities.date_helper import generate_date

from .common_steps import (
    send_update_for_immunization_event,
    trigger_the_updated_request,
    valid_json_payload_is_created,
    valid_token_is_generated,
)

scenarios("APITests/update.feature")


@when(parsers.parse("Send a update for Immunization event created with patient address being updated by '{Supplier}'"))
def send_update_for_immunization_event_by_supplier(context, Supplier):
    valid_token_is_generated(context, Supplier)
    send_update_for_immunization_event(context)


@when(
    parsers.parse("Send a update for Immunization event created with occurrenceDateTime being updated to '{DateText}'")
)
def send_update_for_immunization_event_with_occurrenceDateTime(context, DateText):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.occurrenceDateTime = generate_date(DateText)
    trigger_the_updated_request(context)


@when(parsers.parse("Send a update for Immunization event created with recorded being updated to '{DateText}'"))
def send_update_for_immunization_event_with_recorded_date_update(context, DateText):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.recorded = generate_date(DateText)
    trigger_the_updated_request(context)


@when(
    parsers.parse("Send a update for Immunization event created with patient date of bith being updated to '{DateText}'")
)
def send_update_for_immunization_event_with_dob_update(context, DateText):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.contained[1].birthDate = generate_date(DateText)
    trigger_the_updated_request(context)


@when(parsers.parse("Send a update for Immunization event created with expiration date being updated to '{DateText}'"))
def send_update_for_immunization_event_with_expiration_date_update(context, DateText):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    context.update_object.expirationDate = generate_date(DateText)
    trigger_the_updated_request(context)


@when("Send an update request for invalid immunization id")
def send_update_request_for_invalid_immunization_id(context):
    valid_json_payload_is_created(context)
    context.ImmsID = str(uuid.uuid4())
    get_update_url_header(context, str(context.expected_version))
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    trigger_the_updated_request(context)


@when(parsers.parse("Send an update request for invalid Etag {Etag}"))
def send_update_request_for_invalid_etag(context, Etag):
    valid_json_payload_is_created(context)
    context.ImmsID = str(uuid.uuid4())
    context.version = Etag
    get_update_url_header(context, Etag)
    context.update_object = copy.deepcopy(context.immunization_object)
    context.update_object = convert_to_update(context.update_object, context.ImmsID)
    trigger_the_updated_request(context)


@then(parsers.parse("The Response JSONs should contain correct error message for etag '{errorName}'"))
def validateForbiddenAccess(context, errorName):
    error_response = parse_error_response(context.response.json())
    validate_error_response(error_response, errorName, version=context.version)
    print(f"\n Error Response - \n {error_response}")
