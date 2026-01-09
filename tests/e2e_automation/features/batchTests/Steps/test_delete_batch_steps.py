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
from features.APITests.steps.test_delete_steps import validate_imms_delta_table_by_deleted_ImmsID

scenarios('batchTests/delete_batch.feature')

@given("batch file is created for below data as full dataset and each record has a valid delete record in the same file")
@ignore_if_local_run
def valid_batch_file_is_created_with_details(datatable, context):    
    build_dataFrame_using_datatable(datatable, context) 
    df_new = context.vaccine_df.copy()
    df_update = df_new.copy()
    df_update["ACTION_FLAG"] = "DELETE"
    context.vaccine_df = pd.concat([df_new, df_update], ignore_index=True)      
    create_batch_file(context)
    
@given("I have created a valid vaccination record through API")
def create_valid_vaccination_record_through_api(context):
    validVaccinationRecordIsCreated(context)
    print(f"Created Immunization record with ImmsID: {context.ImmsID}")
    
@when("An delete to above vaccination record is made through batch file upload")
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
                                "DELETE",
                                context.create_object.identifier[0].value,
                                context.create_object.identifier[0].system
                            ]
    create_batch_file(context) 
    context.vaccine_df.loc[0, "IMMS_ID"] = context.ImmsID 
   
@then("The delta and imms event table will be populated with the correct data for api created event")    
@given("The delta and imms event table will be populated with the correct data for api created event")
def validate_imms_delta_table_for_api_created_event(context):
    validate_imms_event_table_by_operation(context, "created")
    validate_imms_delta_table_by_ImmsID(context)    
    
@when("Delete above vaccination record is made through batch file upload with mandatory field missing")
def upload_batch_file_to_s3_for_update_with_mandatory_field_missing(context):
    # Build base record
    record = build_batch_file(context)
    context.vaccine_df = pd.DataFrame([record.dict()])

    base_fields = {
        "NHS_NUMBER": context.create_object.contained[1].identifier[0].value,
        "PERSON_FORENAME": context.create_object.contained[1].name[0].given[0],
        "PERSON_SURNAME": context.create_object.contained[1].name[0].family,
        "PERSON_GENDER_CODE": context.create_object.contained[1].gender,
        "PERSON_DOB": "",
        "PERSON_POSTCODE": context.create_object.contained[1].address[0].postalCode,
        "ACTION_FLAG": "DELETE",
        "UNIQUE_ID": context.create_object.identifier[0].value,
        "UNIQUE_ID_URI": context.create_object.identifier[0].system,
    }
    context.vaccine_df.loc[0, list(base_fields.keys())] = list(base_fields.values())

    create_batch_file(context)
    context.vaccine_df.loc[0, "IMMS_ID"] = context.ImmsID   


@then("The imms event table status will be updated to delete and no change to record detail")
def validate_imms_event_table_for_delete_event(context):
    validate_imms_event_table_by_operation(context, "deleted")
    
@then("The delta table will have delete entry with no change to record detail")
def validate_delta_table_for_delete_event(context):
    validate_imms_delta_table_by_deleted_ImmsID(context)