import json
from urllib.parse import parse_qs
from venv import logger
import requests
from pytest_bdd import given, when, then, parsers
from src.dynamoDB.dynamo_db_helper import *
from src.objectModels.patient_loader import load_patient_by_id
from src.objectModels.api_immunization_builder import *
from utilities.api_fhir_immunization_helper import *
from utilities.enums import Operation
from utilities.api_gen_token import get_tokens
from utilities.api_get_header import *
import pytest_check as check
from utilities.date_helper import *

    
@given(parsers.parse("Valid token is generated for the '{Supplier}'"))
def valid_token_is_generated(context, Supplier):
    context.supplier_name = Supplier
    get_tokens(context, Supplier)
    
@given("Valid json payload is created")
def valid_json_payload_is_created(context):
    context.patient = load_patient_by_id(context.patient_id)
    context.immunization_object = create_immunization_object(context.patient, context.vaccine_type)

@given(parsers.parse("Valid json payload is created with Patient '{Patient}' and vaccine_type '{vaccine_type}'"))
def The_Immunization_object_is_created_with_patient_for_vaccine_type(context, Patient, vaccine_type):
    context.vaccine_type = vaccine_type
    context.patient_id = Patient
    context.patient = load_patient_by_id(context.patient_id)
    context.immunization_object = create_immunization_object(context.patient, context.vaccine_type)
    
@given(parsers.parse("Valid vaccination record is created with Patient '{Patient}' and vaccine_type '{vaccine_type}'"))
def validVaccinationRecordIsCreatedWithPatient(context, Patient, vaccine_type):
    The_Immunization_object_is_created_with_patient_for_vaccine_type(context, Patient, vaccine_type)
    Trigger_the_post_create_request(context)
    The_request_will_have_status_code(context, 201)
    validateCreateLocation(context)
        
@given("I have created a valid vaccination record")
def validVaccinationRecordIsCreated(context):
    valid_json_payload_is_created(context)
    Trigger_the_post_create_request(context)
    The_request_will_have_status_code(context, 201)
    validateCreateLocation(context)
    
@given(parsers.parse("valid vaccination record is created by '{Supplier}' supplier"))
def valid_vaccination_record_is_created_by_supplier(context, Supplier):
    valid_token_is_generated(context, Supplier)
    validVaccinationRecordIsCreated(context)
    
@when("Trigger the post create request")
def Trigger_the_post_create_request(context):
    get_create_post_url_header(context)
    context.create_object = context.immunization_object
    context.request = context.create_object.dict(exclude_none=True, exclude_unset=True)
    context.response = requests.post(context.url, json=context.request, headers=context.headers)
    print(f"Create Request is {json.dumps(context.request)}" )

@then(parsers.parse("The request will be unsuccessful with the status code '{statusCode}'"))
@then(parsers.parse("The request will be successful with the status code '{statusCode}'"))
def The_request_will_have_status_code(context, statusCode):
    print(context.response.status_code)
    print(int(statusCode))
    assert context.response.status_code == int(statusCode), f"\n Expected status code: {statusCode}, but got: {context.response.status_code}. Response: {context.response.json()} \n"


@then('The location key and Etag in header will contain the Immunization Id and version')
def validateCreateLocation(context):
    location = context.response.headers['location']
    eTag = context.response.headers['E-Tag']
    assert  "location" in context.response.headers, f"Location header is missing in the response with Status code: {context.response.statusCode}. Response: {context.response.json()}"
    assert  "E-Tag" in context.response.headers, f"E-Tag header is missing in the response with Status code: {context.response.statusCode}. Response: {context.response.json()}"
    context.ImmsID = location.split("/")[-1]
    context.eTag= eTag.strip('"')
    print(f"\n Immunization ID is {context.ImmsID} and Etag is {context.eTag} \n")
    check.is_true(
        context.ImmsID is not None, 
        f"Expected IdentifierPK: {context.patient.identifier[0].value}, Found: {context.ImmsID}"
    )

@then('The Search Response JSONs should contain correct error message for invalid NHS Number')   
@then('The Search Response JSONs should contain correct error message for invalid Disease Type')   
@then('The Search Response JSONs should contain correct error message for invalid Date From')
@then('The Search Response JSONs should contain correct error message for invalid Date To')
@then('The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority') 
@then('The Search Response JSONs should contain correct error message for invalid include')
@then('The Search Response JSONs should contain correct error message for invalid Date From and Date To')
@then('The Search Response JSONs should contain correct error message for invalid Date From, Date To and include')
def operationOutcomeInvalidParams(context):
    error_response = parse_error_response(context.response.json())
    params = getattr(context, "params", getattr(context, "request", {}))
    
    if isinstance(params, str):
        parsed = parse_qs(params)
        params = {k: v[0] for k, v in parsed.items()} if parsed else {}

    date_from_value = params.get("-date.from")
    date_to_value = params.get("-date.to")
    include_value = params.get("_include")
    nhs_number= params.get("patient.identifier").replace("https://fhir.nhs.uk/Id/nhs-number|", "") 
    disease_type= params.get("-immunization.target")

    # Validation flags
    nhs_invalid =  not is_valid_nhs_number(nhs_number)
    disease_invalid =  not is_valid_disease_type(disease_type)
    date_from_invalid = date_from_value and not is_valid_date(date_from_value)
    date_to_invalid =  date_to_value and not is_valid_date(date_to_value)
    include_invalid =  include_value != "Immunization:patient"

    match (nhs_invalid, disease_invalid, date_from_invalid, date_to_invalid, include_invalid):
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
     
@then('The X-Request-ID and X-Correlation-ID keys in header will populate correctly')
def validateCreateHeader(context):
    assert "X-Request-ID" in context.response.request.headers, "X-Request-ID missing in headers"
    assert "X-Correlation-ID" in context.response.request.headers, "X-Correlation-ID missing in headers"
    assert context.response.request.headers["X-Request-ID"] == context.reqID, "X-Request-ID incorrect"
    assert context.response.request.headers["X-Correlation-ID"] == context.corrID, "X-Correlation-ID incorrect"   
    
@then(parsers.parse("The imms event table will be populated with the correct data for '{operation}' event"))
def validate_imms_event_table_by_operation(context, operation: Operation):
    create_obj = context.create_object
    table_query_response = fetch_immunization_events_detail(context.aws_profile_name, context.ImmsID, context.S3_env)
    assert "Item" in table_query_response, f"Item not found in response for ImmsID: {context.ImmsID}"
    item = table_query_response["Item"]

    resource_json_str = item.get("Resource")
    assert resource_json_str, "Resource field missing in item."

    try:
        resource = json.loads(resource_json_str)
    except (TypeError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse Resource from item: {e}")
        raise AssertionError("Failed to parse Resource from response item.")

    assert resource is not None, "Resource is None in the response"
    created_event = parse_imms_int_imms_event_response(resource)
    
    assert int(context.expected_version) == int(context.eTag), (
        f"Expected Version: {context.expected_version}, Found: {context.eTag}"
    )
    
    fields_to_compare = [
        ("Operation", Operation[operation].value, item.get("Operation")),
        ("SupplierSystem", context.supplier_name.upper(), item.get("SupplierSystem").upper()),
        ("PatientPK", f"Patient#{context.patient.identifier[0].value}", item.get("PatientPK")),
        ("PatientSK", f"{context.vaccine_type.upper()}#{context.ImmsID}", item.get("PatientSK")),
         ("Version", int(context.expected_version), int(item.get("Version"))),
    ]
    
    for name, expected, actual in fields_to_compare:
        check.is_true(
                expected == actual,
                f"Expected {name}: {expected}, Actual {actual}"
            )
        
    validate_to_compare_request_and_response(context, create_obj, created_event, True)

@then(parsers.parse("The Response JSONs should contain correct error message for '{errorName}'"))
@then(parsers.parse("The Response JSONs should contain correct error message for '{errorName}' access"))
@then(parsers.parse("The Response JSONs should contain correct error message for Imms_id '{errorName}'"))
def validateForbiddenAccess(context, errorName):
    error_response = parse_error_response(context.response.json())
    validate_error_response(error_response, errorName, imms_id=context.ImmsID)
    print(f"\n Error Response - \n {error_response}")
    
@then('The Etag in header will containing the latest event version')
def validate_etag_in_header(context):
    etag = context.response.headers['E-Tag']
    assert etag, "Etag header is missing in the response"
    context.eTag= etag.strip('"')
    assert context.eTag == str(context.expected_version), f"Etag version mismatch: expected {context.expected_version}, got {context.eTag}"
    
@when('Send a update for Immunization event created with vaccination detail being updated')
def send_update_for_vaccination_detail(context):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = convert_to_update(context.immunization_object, context.ImmsID)
    context.expected_version = int(context.expected_version) + 1
    context.update_object.extension = [build_vaccine_procedure_extension(context.vaccine_type.upper())]
    vaccine_details = get_vaccine_details(context.vaccine_type.upper())
    context.update_object.vaccineCode = vaccine_details["vaccine_code"]
    context.update_object.site = build_site_route(random.choice(SITE_MAP))
    context.update_object.route = build_site_route(random.choice(ROUTE_MAP))
    context.create_object = context.update_object
    context.request = context.update_object.dict(exclude_none=True, exclude_unset=True)
    context.response = requests.put(context.url + "/" + context.ImmsID, json=context.request, headers=context.headers)
    print(f"Update Request is {json.dumps(context.request)}" )
    
@when('Send a update for Immunization event created with patient address being updated')
def send_update_for_immunization_event(context):
    get_update_url_header(context, str(context.expected_version))
    context.update_object = convert_to_update(context.immunization_object, context.ImmsID)
    context.update_object.contained[1].address[0].city = "Updated City"
    context.update_object.contained[1].address[0].state = "Updated State"
    trigger_the_updated_request(context)
      
@given('created event is being updated twice')
def created_event_is_being_updated_twice(context):
    send_update_for_immunization_event(context)
    The_request_will_have_status_code(context, 200)
    send_update_for_vaccination_detail(context)
    The_request_will_have_status_code(context, 200)
    
@given('created event is being deleted')
def created_event_is_being_deleted(context):
    send_delete_for_immunization_event_created(context)
    The_request_will_have_status_code(context, 204)
    
@when('Send a delete for Immunization event created')
def send_delete_for_immunization_event_created(context):
    get_delete_url_header(context)
    print(f"\n Delete Request is {context.url}/{context.ImmsID}")
    context.response = requests.delete(f"{context.url}/{context.ImmsID}", headers=context.headers)
    
def trigger_the_updated_request(context):
    context.expected_version = int(context.expected_version) + 1    
    context.create_object = context.update_object
    context.request = context.update_object.dict(exclude_none=True, exclude_unset=True)
    context.response = requests.put(context.url + "/" + context.ImmsID, json=context.request, headers=context.headers)
    print(f"Update Request is {json.dumps(context.request)}" )
    
def normalize_param(value: str) -> str:
    return "" if value.lower() in {"none", "null", ""} else value