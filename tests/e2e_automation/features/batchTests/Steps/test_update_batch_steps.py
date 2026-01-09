from multiprocessing import context
from src.dynamoDB.dynamo_db_helper import *
from src.objectModels.api_immunization_builder import *
from src.objectModels.batch.batch_file_builder import *
from utilities.batch_S3_buckets import *
from utilities.batch_file_helper import *
from utilities.date_helper import *
from utilities.text_helper import get_text
from utilities.vaccination_constants import *
from pytest_bdd import scenarios, given, when, then, parsers
import pytest_check as check
from .batch_common_steps import *
from features.APITests.steps.common_steps import *
from features.APITests.steps.test_create_steps import validate_imms_delta_table_by_ImmsID
from features.APITests.steps.test_update_steps import validate_delta_table_for_updated_event

scenarios('batchTests/update_batch.feature')

@given("batch file is created for below data as full dataset and each record has a valid update record in the same file")
def valid_batch_file_is_created_with_details(datatable, context):    
    build_dataFrame_using_datatable(datatable, context) 
    df_new = context.vaccine_df.copy()
    df_update = df_new.copy()
    df_update[["ACTION_FLAG", "EXPIRY_DATE"]] = ["UPDATE", "20281231"]
    context.vaccine_df = pd.concat([df_new, df_update], ignore_index=True) 
    context.expected_version = 2      
    create_batch_file(context)
    
@given("I have created a valid vaccination record through API")
def create_valid_vaccination_record_through_api(context):
    validVaccinationRecordIsCreated(context)
    print(f"Created Immunization record with ImmsID: {context.ImmsID}")
    
    
    
@when("An update to above  vaccination record is made through batch file upload")
def upload_batch_file_to_s3_for_update(context):
    record = build_batch_file(context)
    context.vaccine_df = pd.DataFrame([record.dict()]) 
    context.vaccine_df.loc[0, [
                                "NHS_NUMBER",
                                "PERSON_FORENAME",
                                "PERSON_SURNAME",
                                "PERSON_GENDER_CODE",
                                "PERSON_DOB",
                                "PERSON_POSTCODE",
                                "ACTION_FLAG",
                                "UNIQUE_ID",
                                "UNIQUE_ID_URI"
                            ]] = [
                                context.create_object.contained[1].identifier[0].value,
                                context.create_object.contained[1].name[0].given[0],
                                context.create_object.contained[1].name[0].family,
                                context.create_object.contained[1].gender,
                                context.create_object.contained[1].birthDate.replace("-", ""),
                                context.create_object.contained[1].address[0].postalCode,
                                "UPDATE",
                                context.create_object.identifier[0].value,
                                context.create_object.identifier[0].system
                            ]
    context.expected_version = 2 
    create_batch_file(context) 
   
@then("The delta and imms event table will be populated with the correct data for api created event")    
@given("The delta and imms event table will be populated with the correct data for api created event")
def validate_imms_delta_table_for_api_created_event(context):
    validate_imms_event_table_by_operation(context, "created")
    validate_imms_delta_table_by_ImmsID(context)
    
@when("Send a update for Immunization event created with vaccination detail being updated through API request")
def send_update_for_immunization_event_with_vaccination_detail_updated(context):
    valid_json_payload_is_created(context)
    row = context.vaccine_df.loc[0]
    context.immunization_object.contained[1].identifier[0].value = row["NHS_NUMBER"]
    context.immunization_object.contained[1].name[0].given[0] = row["PERSON_FORENAME"]
    context.immunization_object.contained[1].name[0].family = row["PERSON_SURNAME"]
    reverse_gender_map = {v.value: v.name for v in GenderCode}
    code = row["PERSON_GENDER_CODE"]
    context.immunization_object.contained[1].gender = reverse_gender_map.get(code, "unknown")
    context.immunization_object.contained[1].birthDate = (
                        f"{row['PERSON_DOB'][:4]}-{row['PERSON_DOB'][4:6]}-{row['PERSON_DOB'][6:]}"
                            )
    context.immunization_object.contained[1].address[0].postalCode = row["PERSON_POSTCODE"]
    context.immunization_object.identifier[0].value = row["UNIQUE_ID"]
    context.immunization_object.identifier[0].system = row["UNIQUE_ID_URI"]
    send_update_for_immunization_event(context) 
    
@then("Api request will be successful and tables will be updated correctly")
def api_request_will_be_successful_and_tables_will_be_updated_correctly(context):
    The_request_will_have_status_code(context, 200)
    validate_etag_in_header(context)
    validate_imms_event_table_by_operation(context, "updated")
    validate_delta_table_for_updated_event(context)
    
@when("Update to above vaccination record is made through batch file upload with mandatory field missing")
def upload_batch_file_to_s3_for_update_with_mandatory_field_missing(context):
    # Build base record
    record = build_batch_file(context)
    context.vaccine_df = pd.DataFrame([record.dict()])

    base_fields = {
        "NHS_NUMBER": context.create_object.contained[1].identifier[0].value,
        "PERSON_FORENAME": context.create_object.contained[1].name[0].given[0],
        "PERSON_SURNAME": context.create_object.contained[1].name[0].family,
        "PERSON_GENDER_CODE": context.create_object.contained[1].gender,
        "PERSON_DOB": context.create_object.contained[1].birthDate.replace("-", ""),
        "PERSON_POSTCODE": context.create_object.contained[1].address[0].postalCode,
        "ACTION_FLAG": "UPDATE",
        "UNIQUE_ID": context.create_object.identifier[0].value,
        "UNIQUE_ID_URI": context.create_object.identifier[0].system,
    }

    context.vaccine_df.loc[0, list(base_fields.keys())] = list(base_fields.values())

    context.vaccine_df = pd.concat([context.vaccine_df.loc[[0]]] * 19, ignore_index=True)

    missing_cases = {
        0: {"SITE_CODE": "", "PERSON_SURNAME": "empty_site_code"},
        1: {"SITE_CODE_TYPE_URI": "", "PERSON_SURNAME": "empty_site_code_uri"},
        2: {"LOCATION_CODE": "", "PERSON_SURNAME": "empty_location_code"},
        3: {"LOCATION_CODE_TYPE_URI": "", "PERSON_SURNAME": "empty_location_code_uri"},
        4: {"UNIQUE_ID": "", "PERSON_SURNAME": "no_unique_identifiers"},
        5: {"UNIQUE_ID_URI": "", "PERSON_SURNAME": "no_unique_identifiers"},
        6: {"PRIMARY_SOURCE": "", "PERSON_SURNAME": "empty_primary_source"},
        7: {"VACCINATION_PROCEDURE_CODE": "", "PERSON_SURNAME": "no_procedure_code"},
        8: {"SITE_CODE": " ", "PERSON_SURNAME": "no_site_code"},
        9: {"SITE_CODE_TYPE_URI": " ", "PERSON_SURNAME": "no_site_code_uri"},
        10: {"LOCATION_CODE": " ", "PERSON_SURNAME": "no_location_code"},
        11: {"LOCATION_CODE_TYPE_URI": " ", "PERSON_SURNAME": "no_location_code_uri"},
        12: {"UNIQUE_ID": " ", "PERSON_SURNAME": "no_unique_id"},
        13: {"UNIQUE_ID_URI": " ", "PERSON_SURNAME": "no_unique_id_uri"},
        14: {"PRIMARY_SOURCE": " ", "PERSON_SURNAME": "no_primary_source"},
        15: {"VACCINATION_PROCEDURE_CODE": " ", "PERSON_SURNAME": "empty_procedure_code"},
        16: {"PRIMARY_SOURCE": "test", "PERSON_SURNAME": "no_primary_source"},
        17: {"ACTION_FLAG": "", "PERSON_SURNAME": "invalid_action_flag"},
        18: {"ACTION_FLAG": " ", "PERSON_SURNAME": "invalid_action_flag"}
    }

    # Apply all missing-field modifications
    for row_idx, updates in missing_cases.items():
        for col, value in updates.items():
            context.vaccine_df.loc[row_idx, col] = value

    create_batch_file(context)

@then("bus ack will have error records for all the updated records in the batch file")
def all_records_are_processed_successfully_in_the_batch_file(context): 
    file_rows = read_and_validate_bus_ack_file_content(context, False, True) 
    all_valid = validate_bus_ack_file_for_error_by_surname(context, file_rows)
    assert all_valid, "One or more records failed validation checks"

def validate_bus_ack_file_for_error_by_surname(context, file_rows) -> bool:
    if not file_rows:
        print("No rows found in BUS ACK file for failed records")
        return False

    overall_valid = True

    for batch_idx, row in context.vaccine_df.iterrows():

        bus_ack_row_number = batch_idx + 2

        row_data_list = file_rows.get(bus_ack_row_number)

        if not row_data_list:
            print(f"Batch row {batch_idx}: No BUS ACK entry found for row number {bus_ack_row_number}")
            overall_valid = False
            continue

        surname = str(row.get("PERSON_SURNAME", "")).strip()
        expected_error = surname
        expected_diagnostic = ERROR_MAP.get(expected_error, {}).get("diagnostics")

        for row_data in row_data_list:
            i = row_data["row"]
            fields = row_data["fields"]
            row_valid = True

            header_response_code = fields[1]
            issue_severity = fields[2]
            issue_code = fields[3]
            response_code = fields[6]
            response_display = fields[7]
            imms_id = fields[11]
            operation_outcome = fields[12]
            message_delivery = fields[13]


            if header_response_code != "Fatal Error":
                print(f"Row {i}: HEADER_RESPONSE_CODE is not 'Fatal Error'")
                row_valid = False
            if issue_severity != "Fatal":
                print(f"Row {i}: ISSUE_SEVERITY is not 'Fatal'")
                row_valid = False
            if issue_code != "Fatal Error":
                print(f"Row {i}: ISSUE_CODE is not 'Fatal Error'")
                row_valid = False
            if response_code != "30002":
                print(f"Row {i}: RESPONSE_CODE is not '30002'")
                row_valid = False
            if response_display != "Business Level Response Value - Processing Error":
                print(f"Row {i}: RESPONSE_DISPLAY is not expected value")
                row_valid = False
            if imms_id:
                print(f"Row {i}: IMMS_ID should be null but is populated")
                row_valid = False
            if message_delivery != "False":
                print(f"Row {i}: MESSAGE_DELIVERY is not 'False'")
                row_valid = False

            if operation_outcome != expected_diagnostic:
                print(
                    f"Row {i}: operation_outcome '{operation_outcome}' does not match "
                    f"expected diagnostics '{expected_diagnostic}' for surname '{expected_error}'"
                )
                row_valid = False

            overall_valid = overall_valid and row_valid

    return overall_valid