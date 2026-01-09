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

scenarios('batchTests/create_batch.feature')
   
@given("batch file is created for below data as minimum dataset")
@ignore_if_local_run
def valid_batch_file_is_created_with_minimum_details(datatable, context):
    build_dataFrame_using_datatable(datatable, context)
    columns_to_clear = [
        "NHS_NUMBER", "VACCINATION_PROCEDURE_TERM", "VACCINE_PRODUCT_CODE", "VACCINE_PRODUCT_TERM", "VACCINE_MANUFACTURER", "BATCH_NUMBER", "SITE_OF_VACCINATION_CODE", "SITE_OF_VACCINATION_TERM", "EXPIRY_DATE",
        "ROUTE_OF_VACCINATION_CODE", "ROUTE_OF_VACCINATION_TERM", "DOSE_SEQUENCE", "DOSE_AMOUNT", "DOSE_UNIT_CODE", "DOSE_UNIT_TERM", "INDICATION_CODE", "PERFORMING_PROFESSIONAL_SURNAME", "PERFORMING_PROFESSIONAL_FORENAME"
        ]
    context.vaccine_df.loc[:, columns_to_clear] = ""
    create_batch_file(context)
    
@given("batch file is created for below data where date_and_time field has invalid date")
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_date_and_time(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df['DATE_AND_TIME'] = context.vaccine_df['UNIQUE_ID'].apply(lambda uid: get_batch_date(uid.split('-')[1]))     
    create_batch_file(context)   
    
@given("batch file is created for below data where recorded field has invalid date")
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_recorded_date(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df['RECORDED_DATE'] = context.vaccine_df['UNIQUE_ID'].apply(lambda uid: get_batch_date(uid.split('-')[1]))     
    create_batch_file(context)  
  
@given("batch file is created for below data where expiry field has invalid date")  
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_expiry_date(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df['EXPIRY_DATE'] = context.vaccine_df['UNIQUE_ID'].apply(lambda uid: get_batch_date(uid.split('-')[1]))     
    create_batch_file(context) 
    
@given("batch file is created for below data where Person date of birth field has invalid date")  
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_person_dateOfBirth_date(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)   
    context.vaccine_df['PERSON_DOB'] = context.vaccine_df['UNIQUE_ID'].apply(lambda uid: get_batch_date(uid.split('-')[1]))     
    create_batch_file(context) 
    
@given("batch file is created for below data where Person detail has invalid data")
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_patient_data(datatable, context):
    build_dataFrame_using_datatable(datatable, context) 
    context.vaccine_df.loc[0,"NHS_NUMBER"] = "12345678"
    context.vaccine_df.loc[1,"NHS_NUMBER"] = "1234567890"
    context.vaccine_df.loc[2,"PERSON_FORENAME"] = ""
    context.vaccine_df.loc[3,["PERSON_FORENAME", "PERSON_SURNAME"]] = ""
    context.vaccine_df.loc[4,"PERSON_SURNAME"] = ""
    context.vaccine_df.loc[5,"PERSON_GENDER_CODE"] = "8"
    context.vaccine_df.loc[6,"PERSON_GENDER_CODE"] = "unknow"
    context.vaccine_df.loc[7,"PERSON_GENDER_CODE"] = ""
    context.vaccine_df.loc[8,"PERSON_FORENAME"] = " "
    context.vaccine_df.loc[9,"PERSON_SURNAME"] = " "
    context.vaccine_df.loc[10,"PERSON_SURNAME"] = get_text("name_length_36")
    context.vaccine_df.loc[11,"PERSON_FORENAME"] = get_text("name_length_36")
    create_batch_file(context) 
    
@given("batch file is created for below data where performer detail has invalid data")
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_performer_data(datatable, context):
    build_dataFrame_using_datatable(datatable, context) 
    context.vaccine_df.loc[0,"PERFORMING_PROFESSIONAL_FORENAME"] = ""
    context.vaccine_df.loc[1,"PERFORMING_PROFESSIONAL_SURNAME"] = ""
    create_batch_file(context) 
    
@given("batch file is created for below data where person detail has valid values")
@ignore_if_local_run
def valid_batch_file_is_created_with_different_values_gender(datatable, context):
    build_dataFrame_using_datatable(datatable, context) 
    context.vaccine_df.loc[0,"PERSON_GENDER_CODE"] = "0"
    context.vaccine_df.loc[1,"PERSON_GENDER_CODE"] = "1"
    context.vaccine_df.loc[2,"PERSON_GENDER_CODE"] = "2"
    context.vaccine_df.loc[3,"PERSON_GENDER_CODE"] = "9"
    context.vaccine_df.loc[4,"PERSON_GENDER_CODE"] = "unknown"
    context.vaccine_df.loc[5,"PERSON_GENDER_CODE"] = "male"
    context.vaccine_df.loc[6,"PERSON_GENDER_CODE"] = "female"
    context.vaccine_df.loc[7,"PERSON_GENDER_CODE"] = "other"
    context.vaccine_df.loc[8,"PERSON_SURNAME"] = get_text("name_length_35")
    context.vaccine_df.loc[9,"PERSON_FORENAME"] = get_text("name_length_35")
    context.vaccine_df.loc[10,"PERSON_FORENAME"] = f'Elan {get_text("name_length_15")}'
    create_batch_file(context)
    
@given("batch file is created for below data where mandatory fields for site, location, action flag, primary source and unique identifiers are missing")
@ignore_if_local_run
def valid_batch_file_is_created_with_missing_mandatory_fields(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)        
    context.vaccine_df.loc[0, "SITE_CODE"] = ""
    context.vaccine_df.loc[1, "SITE_CODE_TYPE_URI"] = ""
    context.vaccine_df.loc[2, "LOCATION_CODE"] = ""
    context.vaccine_df.loc[3, "LOCATION_CODE_TYPE_URI"] = ""
    context.vaccine_df.loc[4, ["UNIQUE_ID","PERSON_SURNAME"]] = ["", "no_unique_identifiers"]
    context.vaccine_df.loc[5, ["UNIQUE_ID_URI", "PERSON_SURNAME"]] = ["", "no_unique_identifiers"]
    context.vaccine_df.loc[6, "PRIMARY_SOURCE"] = ""
    context.vaccine_df.loc[7, "VACCINATION_PROCEDURE_CODE"] = ""
    context.vaccine_df.loc[8, "SITE_CODE"] = " "
    context.vaccine_df.loc[9, "SITE_CODE_TYPE_URI"] = " "
    context.vaccine_df.loc[10, "LOCATION_CODE"] = " "
    context.vaccine_df.loc[11, "LOCATION_CODE_TYPE_URI"] = " "
    context.vaccine_df.loc[12, ["UNIQUE_ID","PERSON_SURNAME"]] = [" ", "no_unique_id"]
    context.vaccine_df.loc[13, ["UNIQUE_ID_URI", "PERSON_SURNAME"]] = [" ", "no_unique_id_uri"]
    context.vaccine_df.loc[14, "PRIMARY_SOURCE"] = " "
    context.vaccine_df.loc[15, "VACCINATION_PROCEDURE_CODE"] = " "
    context.vaccine_df.loc[16, "PRIMARY_SOURCE"] = "test"
    context.vaccine_df.loc[17, "ACTION_FLAG"]  = ""
    context.vaccine_df.loc[18, "ACTION_FLAG"]  = " "
    create_batch_file(context)
    
@given("batch file is created for below data where mandatory field for site, location and unique uri values are invalid")
@ignore_if_local_run
def valid_batch_file_is_created_with_invalid_mandatory_fields(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)        
    context.vaccine_df.loc[0, "UNIQUE_ID_URI"]  = "invalid_uri"
    context.vaccine_df.loc[1, "SITE_CODE_TYPE_URI"] = "invalid_uri"
    context.vaccine_df.loc[2, "LOCATION_CODE_TYPE_URI"] = "invalid_uri"
    create_batch_file(context)
    
    
@given("batch file is created for below data where action flag has different cases")
@ignore_if_local_run
def valid_batch_file_is_created_with_different_action_flag_cases(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)     
    context.vaccine_df.loc[0, "ACTION_FLAG"]  = "NEW" 
    context.vaccine_df.loc[1, "ACTION_FLAG"]  = "New"  
    context.vaccine_df.loc[2, "ACTION_FLAG"]  = "new"  
    context.vaccine_df.loc[3, "ACTION_FLAG"]  = "nEw"  
    create_batch_file(context)
  
  
@given("batch file is created for below data where non mandatory fields are empty string")  
@ignore_if_local_run
def valid_batch_file_is_created_with_empty_non_mandatory_fields(datatable, context):
    build_dataFrame_using_datatable(datatable, context) 
    context.vaccine_df.loc[0, "NHS_NUMBER"] = " "
    context.vaccine_df.loc[1, "VACCINATION_PROCEDURE_TERM"] = " "
    context.vaccine_df.loc[2, "VACCINE_PRODUCT_CODE"] = " "
    context.vaccine_df.loc[3, "VACCINE_PRODUCT_TERM"] = " "
    context.vaccine_df.loc[4, "VACCINE_MANUFACTURER"] = " "
    context.vaccine_df.loc[5, "BATCH_NUMBER"] = " "
    context.vaccine_df.loc[6, "SITE_OF_VACCINATION_CODE"] = " "
    context.vaccine_df.loc[7, "SITE_OF_VACCINATION_TERM"] = " "
    context.vaccine_df.loc[8, "ROUTE_OF_VACCINATION_CODE"] = " "
    context.vaccine_df.loc[9, "ROUTE_OF_VACCINATION_TERM"] = " "
    context.vaccine_df.loc[10, "DOSE_SEQUENCE"] = " "
    context.vaccine_df.loc[11, "DOSE_UNIT_CODE"] = " "
    context.vaccine_df.loc[12, "DOSE_UNIT_TERM"] = " "
    context.vaccine_df.loc[13, "INDICATION_CODE"] = " "
    create_batch_file(context)
    
@given("batch file is created for below data where non mandatory fields are missing")
@ignore_if_local_run
def valid_batch_file_is_created_with_missing_non_mandatory_fields(datatable, context):  
    build_dataFrame_using_datatable(datatable, context)        
    context.vaccine_df.loc[0, "NHS_NUMBER"] = ""
    context.vaccine_df.loc[1, "VACCINATION_PROCEDURE_TERM"] = ""
    context.vaccine_df.loc[2, "VACCINE_PRODUCT_CODE"] = ""
    context.vaccine_df.loc[3, "VACCINE_PRODUCT_TERM"] = ""
    context.vaccine_df.loc[4, "VACCINE_MANUFACTURER"] = ""
    context.vaccine_df.loc[5, "BATCH_NUMBER"] = ""
    context.vaccine_df.loc[6, "SITE_OF_VACCINATION_CODE"] = ""
    context.vaccine_df.loc[7, "SITE_OF_VACCINATION_TERM"] = ""
    context.vaccine_df.loc[8, "ROUTE_OF_VACCINATION_CODE"] = ""
    context.vaccine_df.loc[9, "ROUTE_OF_VACCINATION_TERM"] = ""
    context.vaccine_df.loc[10, "DOSE_SEQUENCE"] = ""
    context.vaccine_df.loc[11, "DOSE_UNIT_CODE"] = ""
    context.vaccine_df.loc[12, "DOSE_UNIT_TERM"] = ""
    context.vaccine_df.loc[13, "INDICATION_CODE"] = ""
    create_batch_file(context)