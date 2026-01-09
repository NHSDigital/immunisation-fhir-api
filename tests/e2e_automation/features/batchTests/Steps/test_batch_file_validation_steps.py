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

scenarios('batchTests/batch_file_validation.feature')

@given(parsers.parse("batch file is created for below data with {invalid_filename} filename and {file_extension} extension"))
@ignore_if_local_run
def valid_batch_file_is_created_with_details(datatable, context, invalid_filename, file_extension):    
    build_dataFrame_using_datatable(datatable, context)        
    create_batch_file(context,fileName=invalid_filename,file_ext=file_extension)
    
@given("Empty batch file is created")
@ignore_if_local_run
def empty_batch_file_is_created(context): 
    columns = list(BatchVaccinationRecord.__fields__.keys()) 
    context.vaccine_df = pd.DataFrame(columns=columns)   
    create_batch_file(context)
    
@given("batch file is created with missing columns for below data")
@ignore_if_local_run
def batch_file_with_missing_dob_is_created(datatable, context):
    build_dataFrame_using_datatable(datatable, context)
    context.vaccine_df = context.vaccine_df.drop(columns=["PERSON_DOB"])
    context.vaccine_df = context.vaccine_df.drop(columns=["PERFORMING_PROFESSIONAL_FORENAME"])
    create_batch_file(context)
    
@given("batch file is created with invalid column order for below data")
@ignore_if_local_run
def batch_file_with_invalid_column_order_is_created(datatable, context):
    build_dataFrame_using_datatable(datatable, context)
    columns = list(context.vaccine_df.columns)
    columns[0], columns[1] = columns[1], columns[0]
    context.vaccine_df = context.vaccine_df[columns]
    create_batch_file(context)
    
@given("batch file is created with invalid delimiter for below data")
@ignore_if_local_run    
def batch_file_with_invalid_delimiter_is_created(datatable, context):
    build_dataFrame_using_datatable(datatable, context)        
    create_batch_file(context, delimiter= ';')
    
@given("batch file is created with invalid column name for patient surname for below data")
@ignore_if_local_run
def batch_file_with_invalid_column_name_is_created(datatable, context):
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df = context.vaccine_df.rename(columns={"PERSON_SURNAME": "PERSON_SURENAME"})
    create_batch_file(context)
    
@given("batch file is created with additional column person age for below data")
@ignore_if_local_run
def batch_file_with_additional_column_is_created(datatable, context):
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df["PERSON_AGE"] = 30
    create_batch_file(context)
    

@then("file will be moved to destination bucket and inf ack file will be created for duplicate batch file upload")
def file_will_be_moved_to_destination_bucket(context):
    context.fileContent = wait_and_read_ack_file(context, "ack", duplicate_inf_files=True)
    assert context.fileContent, f"File not found in destination bucket after timeout:  {context.forwarded_prefix}"    

@then("inf ack file has failure status for processed batch file")
def failed_inf_ack_file(context):  
    all_valid = validate_inf_ack_file(context, success=False)
    assert all_valid, "One or more records failed validation checks"

@then("bus ack file will not be created")
def file_will_not_be_moved_to_destination_bucket(context):
    context.fileContent = wait_and_read_ack_file(context, "forwardedFile", timeout=10, duplicate_bus_files=True)
    assert context.fileContent==None, f"File found in destination bucket: {context.forwarded_prefix}"

@then(parsers.parse("Audit table will have '{status}', '{queue_name}' and '{error_details}' for the processed batch file"))
def validate_imms_audit_table(context, status, queue_name, error_details):
    table_query_response = fetch_batch_audit_table_detail(context.aws_profile_name, context.filename, context.S3_env)

    assert isinstance(table_query_response, list) and table_query_response, f"Item not found in response for filename: {context.filename}"
    sorted_items = sorted(table_query_response, key=lambda x: x['timestamp'], reverse=True)
    item = sorted_items[0]
    validate_audit_table_record(context, item, status, error_details, queue_name)       
    update_audit_table_for_failed_status(item,context.aws_profile_name, context.S3_env)
