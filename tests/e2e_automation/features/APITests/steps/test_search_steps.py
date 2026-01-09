import requests
import requests
from src.objectModels.api_immunization_builder import *
from src.objectModels.patient_loader import load_patient_by_id
from src.objectModels.api_search_object import *
from utilities.api_get_header import *
import logging
from pytest_bdd import scenarios, given, when, then, parsers
import pytest_check as check
from .common_steps import *
from datetime import datetime
from utilities.api_fhir_immunization_helper import *
from datetime import datetime
from utilities.date_helper import *

scenarios('APITests/search.feature')

@when('Send a search request with Post method using identifier header for Immunization event created')  
def send_search_post_request_with_identifier_header(context):
    get_search_post_url_header(context)
    context.request =  {
             "identifier": f'{context.create_object.identifier[0].system}|{context.create_object.identifier[0].value}'
            }
    print(f"\n Search Post Request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)
    
@when('Send a search request with Post method using identifier and _elements header for Immunization event created')
def send_search_post_request_with_identifier_and_elements_header(context):
    get_search_post_url_header(context)
    context.request =  {
             "identifier": f'{context.create_object.identifier[0].system}|{context.create_object.identifier[0].value}',
             "_elements": "meta,id"
            }
    print(f"\n Search Post Request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)
    
@when('Send a search request with post method using invalid identifier header for Immunization event created')
def send_search_post_request_with_invalid_identifier_header(context):
    get_search_post_url_header(context)
    context.request =  {
             "identifier": f'https://www.ieds.england.nhs.uk/|{str(uuid.uuid4())}',
             "_elements": "meta,id"
            }
    print(f"\n Search Post Request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)

@when("Send a search request with GET method for Immunization event created")
def TriggerSearchGetRequest(context):
    get_search_get_url_header(context)
    context.params = convert_to_form_data(set_request_data(context.patient.identifier[0].value, context.vaccine_type, datetime.today().strftime("%Y-%m-%d")))
    print(f"\n Search Get Parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)
    
    print(f"\n Search Get Response - \n {context.response.json()}")

@when("Send a search request with POST method for Immunization event created")
def TriggerSearchPostRequest(context):
    
    get_search_post_url_header(context)
    context.request = convert_to_form_data(set_request_data(context.patient.identifier[0].value, context.vaccine_type, datetime.today().strftime("%Y-%m-%d")))
    print(f"\n Search Post Request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)
    
    print(f"\n Search Post Response - \n {context.response.json()}")

@when(parsers.parse("Send a search request with GET method with invalid NHS Number '{NHSNumber}' and valid Disease Type '{DiseaseType}'"))
@when(parsers.parse("Send a search request with GET method with valid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"))
@when(parsers.parse("Send a search request with GET method with invalid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"))
def send_invalid_param_get_request(context, NHSNumber, DiseaseType):
    get_search_get_url_header(context)

    NHSNumber = normalize_param(NHSNumber)
    DiseaseType = normalize_param(DiseaseType)
         
    context.params = convert_to_form_data(set_request_data(NHSNumber, DiseaseType, datetime.today().strftime("%Y-%m-%d")))
    print(f"\n Search Get parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)


@when(parsers.parse("Send a search request with POST method with invalid NHS Number '{NHSNumber}' and valid Disease Type '{DiseaseType}'"))
@when(parsers.parse("Send a search request with POST method with valid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"))
@when(parsers.parse("Send a search request with POST method with invalid NHS Number '{NHSNumber}' and invalid Disease Type '{DiseaseType}'"))
def send_invalid_param_post_request(context, NHSNumber, DiseaseType):
    get_search_post_url_header(context)

    NHSNumber = normalize_param(NHSNumber)
    DiseaseType = normalize_param(DiseaseType)      

    context.request = convert_to_form_data(set_request_data(NHSNumber, DiseaseType, datetime.today().strftime("%Y-%m-%d")))
    print(f"\n Search Post request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)


@when(parsers.parse("Send a search request with GET method with invalid Date From '{DateFrom}' and valid Date To '{DateTo}'"))
@when(parsers.parse("Send a search request with GET method with valid Date From '{DateFrom}' and invalid Date To '{DateTo}'"))
@when(parsers.parse("Send a search request with GET method with invalid Date From '{DateFrom}' and invalid Date To '{DateTo}'"))
def send_invalid_date_get_request(context, DateFrom, DateTo):
    get_search_get_url_header(context)

    # DateFrom = normalize_param(DateFrom.lower())
    # DateTo = normalize_param(DateTo.lower())      

    context.params = convert_to_form_data(set_request_data(9001066569, context.vaccine_type, DateFrom, DateTo))
    print(f"\n Search Get parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)

@when(parsers.parse("Send a search request with POST method with invalid Date From '{DateFrom}' and valid Date To '{DateTo}'"))
@when(parsers.parse("Send a search request with POST method with valid Date From '{DateFrom}' and invalid Date To '{DateTo}'"))
@when(parsers.parse("Send a search request with POST method with invalid Date From '{DateFrom}' and invalid Date To '{DateTo}'"))
def send_invalid_param_post_request(context, DateFrom, DateTo):
    get_search_post_url_header(context)

    # DateFrom = normalize_param(DateFrom.lower())
    # DateTo = normalize_param(DateTo)          

    context.request = convert_to_form_data(set_request_data(9001066569, context.vaccine_type, DateFrom, DateTo))
    print(f"\n Search Post request - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)

@when(parsers.parse("Send a search request with GET method with valid NHS Number '{NHSNumber}' and Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}'"))
def send_valid_param_get_request(context, NHSNumber, vaccine_type, DateFrom, DateTo):
    get_search_get_url_header(context)

    context.params = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo))
    print(f"\n Search Get parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)

@when(parsers.parse("Send a search request with POST method with valid NHS Number '{NHSNumber}' and Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}'"))
def send_valid_param_post_request(context, NHSNumber, vaccine_type, DateFrom, DateTo):
    get_search_post_url_header(context)

    context.request = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo))
    print(f"\n Search Get parameters - \n {context.request}") 
    context.response = requests.post(context.url, headers=context.headers, data=context.request)  
 
@when(parsers.parse("Send a search request with GET method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and invalid include '{include}'")) 
def send_valid_param_get_request_with_include(context, NHSNumber, vaccine_type, include):
    get_search_get_url_header(context)
    context.params = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, include=include))
    print(f"\n Search Get parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)
    
@when(parsers.parse("Send a search request with POST method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and invalid include '{include}'"))
def send_valid_param_post_request_with_include(context, NHSNumber, vaccine_type, include):
    get_search_post_url_header(context)
    context.request = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, include=include))
    print(f"\n Search Post parameters - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)
      
@when(parsers.parse("Send a search request with POST method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}' and include '{include}'"))
def send_valid_param_post_request_with_include(context, NHSNumber, vaccine_type, DateFrom, DateTo, include):
    get_search_post_url_header(context)
    context.request = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo, include))
    print(f"\n Search Post parameters - \n {context.request}")
    context.response = requests.post(context.url, headers=context.headers, data=context.request)

@when(parsers.parse("Send a search request with GET method with valid NHS Number '{NHSNumber}' and valid Disease Type '{vaccine_type}' and Date From '{DateFrom}' and Date To '{DateTo}' and include '{include}'"))
def send_valid_param_get_request_with_include(context, NHSNumber, vaccine_type, DateFrom, DateTo, include):
    get_search_get_url_header(context)
    context.params = convert_to_form_data(set_request_data(NHSNumber, vaccine_type, DateFrom, DateTo, include))
    print(f"\n Search Get parameters - \n {context.params}")
    context.response = requests.get(context.url, params = context.params, headers = context.headers)

@then("The occurrenceDateTime of the immunization events should be within the Date From and Date To range")
def validateDateRange(context):
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


@then('The Search Response JSONs should contain the detail of the immunization events created above')
def validateImmsID(context):
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)
    
    assert context.parsed_search_object.resourceType == "Bundle", f"expected resourceType to be 'Bundle' but got {context.parsed_search_object.resourceType}"
    assert context.parsed_search_object.type == "searchset", f"expected resourceType to be 'searchset' but got {context.parsed_search_object.type }"
    assert context.parsed_search_object.link[0].relation == "self" , f"expected link relation to be 'self' but got {context.parsed_search_object.link[0].relation }"
    assert  context.parsed_search_object.link[0].url.startswith(context.baseUrl), f"Expected link URL to start with '{context.baseUrl}', but got '{context.parsed_search_object.link[0].url}'"
    assert context.parsed_search_object.total >= 1, f"expected total to be greater than or equal to 1 but got {context.parsed_search_object.total }"

    context.created_event = find_entry_by_Imms_id(context.parsed_search_object, context.ImmsID)
   
    if context.created_event is None:
        raise AssertionError(f"No object found with Immunisation ID {context.ImmsID} in the search response.")
    
    patient_reference = getattr(context.created_event.resource.patient, "reference", None)

    if not patient_reference:
        raise ValueError("Patient reference is missing in the found event.")

    # Assign to context for further usage
    context.Patient_fullUrl = patient_reference

@then('The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization')
def validateJsonImms(context):
    create_obj = context.create_object
    created_event= context.created_event.resource
    validate_to_compare_request_and_response(context, create_obj, created_event)

@then('The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient')
def validateJsonPat(context):        
    response_patient_entry =  find_patient_by_fullurl(context.parsed_search_object)
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
            check.is_true(
                expected == actual,
                f"Expected {name}: {expected}, Actual {actual}"
            )


@then('correct immunization event is returned in the response')
def validate_correct_immunization_event(context):
    data = context.response.json()
    context.parsed_search_object = parse_FHIR_immunization_response(data)

    context.created_event = context.parsed_search_object.entry[0] if context.parsed_search_object.entry else None
   
    if context.created_event is None:
        raise AssertionError(f"No object found with Immunisation ID {context.ImmsID} in the search response.")
       
    validateJsonImms(context)
    
    assert context.parsed_search_object.resourceType == "Bundle", f"expected resourceType to be 'Bundle' but got {context.parsed_search_object.resourceType}"
    assert context.parsed_search_object.type == "searchset", f"expected resourceType to be 'searchset' but got {context.parsed_search_object.type }"
    assert context.parsed_search_object.link[0].relation == "self" , f"expected link relation to be 'self' but got {context.parsed_search_object.link[0].relation }"
    assert  context.parsed_search_object.link[0].url.startswith(context.baseUrl), f"Expected link URL to start with '{context.baseUrl}', but got '{context.parsed_search_object.link[0].url}'"
    assert context.parsed_search_object.total == 1, f"expected total to be greater than or equal to 1 but got {context.parsed_search_object.total }"

@then('correct immunization event is returned in the response with only specified elements')
def validate_correct_immunization_event_with_elements(context):
    response = context.response.json()
    assert response.get("resourceType") == "Bundle", "resourceType should be 'Bundle'"
    assert response.get("type") == "searchset", "type should be 'searchset'"
    assert isinstance(response.get("entry"), list) and len(response["entry"]) > 0, " entry list is missing or empty"

    # Link validation
    link = response.get("link", [{}])[0]
    link_url = link.get("url")
    assert link_url is not None, " link[0].url is missing"
    assert link_url.startswith(context.baseUrl), f"link[0].url should start with '{context.baseUrl}', got '{link_url}'"

    # Entry resource validation
    resource = response["entry"][0].get("resource", {})
    assert resource.get("resourceType") == "Immunization", "resourceType should be 'Immunization'"
    assert "id" in resource, "resource.id is missing"
    assert "meta" in resource and "versionId" in resource["meta"], " meta.versionId is missing"
    
    assert resource["id"] == context.ImmsID, f"resource.id mismatch: expected '{context.ImmsID}', got '{resource['id']}'"
    assert str(resource["meta"]["versionId"]) == str(context.expected_version),  f"meta.versionId mismatch: expected '{context.expected_version}', got '{resource['meta']['versionId']}'"

    assert response.get("total") == 1, "total should be 1"

@then('Empty immunization event is returned in the response')
def validate_empty_immunization_event(context):
    response = context.response.json()
    assert response.get("resourceType") == "Bundle", "resourceType should be 'Bundle'"
    assert response.get("type") == "searchset", "type should be 'searchset'"
    assert isinstance(response.get("entry"), list) and len(response["entry"]) == 0, " entry list should be empty"

    # Link validation
    link = response.get("link", [{}])[0]
    link_url = link.get("url")
    assert link_url is not None, " link[0].url is missing"
    assert link_url == f"{context.baseUrl}/Immunization?identifier=None", f"link[0].url should be '{context.baseUrl}/Immunization?identifier=None', got '{link_url}'"

    assert response.get("total") == 0, "total should be 0"
