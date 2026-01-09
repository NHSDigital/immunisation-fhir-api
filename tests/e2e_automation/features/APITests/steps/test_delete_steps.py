from .test_search_steps import TriggerSearchGetRequest, TriggerSearchPostRequest
from src.dynamoDB.dynamo_db_helper import *
from src.objectModels.api_immunization_builder import *
from utilities.enums import ActionFlag
from utilities.api_get_header import *
import logging
from pytest_bdd import scenarios, given, when, then, parsers
from .common_steps import *
from utilities.date_helper import *

logging.basicConfig(filename='debugLog.log', level=logging.INFO)
logger = logging.getLogger(__name__)


scenarios('APITests/delete.feature')

@when('Send a delete for Immunization event created with invalid Imms Id')
def send_delete_for_immunization_event_created_invalid(context):
    get_delete_url_header(context)
    context.ImmsID = str(uuid.uuid4())
    print(f"\n Delete Request is {context.url}/{context.ImmsID}")
    context.response = requests.delete(f"{context.url}/{context.ImmsID}", headers=context.headers)

    
@when(parsers.parse("Send a delete for Immunization event created for the above created event is send by '{Supplier}'"))
def send_delete_for_immunization_event_by_supplier(context, Supplier):
    valid_token_is_generated(context, Supplier)
    send_delete_for_immunization_event_created(context)
    
@then('The delta table will be populated with the correct data for deleted event')
def validate_imms_delta_table_by_deleted_ImmsID(context):
    create_obj = context.create_object
    items = fetch_immunization_int_delta_detail_by_immsID(context.aws_profile_name, context.ImmsID, context.S3_env, 2)
    assert items, f"Items not found in response for ImmsID: {context.ImmsID}"

    # Find the latest item where operation is DELETE
    deleted_items = [i for i in items if i.get('Operation') == Operation.deleted.value]
    assert deleted_items, f"No deleted item found for ImmsID: {context.ImmsID}"

    # Assuming each item has a 'timestamp' field to determine the latest
    item = [max(deleted_items, key=lambda x: x.get('timestamp', 0))]
     
    validate_imms_delta_record_with_created_event(context, create_obj, item, Operation.deleted.value, ActionFlag.deleted.value) 
    
@then('Deleted Immunization event will not be present in Get method Search API response')
def validate_deleted_immunization_event_not_present(context):
    TriggerSearchGetRequest(context)
    The_request_will_have_status_code(context, '200')
    
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)

    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)
   
    assert context.created_event is None, f"Immunization event with ID {context.ImmsID} should not be present in the search response after deletion."
    
@then('Deleted Immunization event will not be present in Post method Search API response')
def validate_deleted_immunization_event_not_present(context):
    TriggerSearchPostRequest(context)
    The_request_will_have_status_code(context, '200')
    
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)

    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)
   
    assert context.created_event is None, f"Immunization event with ID {context.ImmsID} should not be present in the search response after deletion."