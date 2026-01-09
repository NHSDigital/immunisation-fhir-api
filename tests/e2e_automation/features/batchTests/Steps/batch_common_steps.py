from concurrent.futures import thread
import json
import pandas as pd
import os
from src.dynamoDB.dynamo_db_helper import *
from src.objectModels.api_immunization_builder import *
from src.objectModels.patient_loader import load_patient_by_id
from datetime import datetime, timedelta, timezone
from src.objectModels.batch.batch_file_builder import *
from utilities.batch_S3_buckets import *
from utilities.batch_file_helper import *
from utilities.date_helper import *
from utilities.enums import ActionFlag, Operation
from utilities.vaccination_constants import *
from pytest_bdd import scenarios, given, when, then, parsers
import pytest_check as check
import functools

def ignore_if_local_run(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context from args or kwargs
        context = kwargs.get("context") if "context" in kwargs else (args[-1] if args else None)

        if context and getattr(context, "LOCAL_RUN_WITHOUT_S3_UPLOAD", False):
            print(f"Skipping step '{func.__name__}' due to local execution mode.")
            return None
        return func(*args, **kwargs)
    return wrapper

def ignore_local_run_set_test_data(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context from args or kwargs
        context = kwargs.get("context") if "context" in kwargs else (args[-1] if args else None)

        if context and getattr(context, "LOCAL_RUN_WITHOUT_S3_UPLOAD", False):
            print(f"Skipping step '{func.__name__}' due to local execution mode.")

            file_name = os.getenv("LOCAL_RUN_FILE_NAME")
            context.filename = file_name
            file_path = os.path.join(context.working_directory, file_name)

            # Read file into vaccine_df
            try:
                context.vaccine_df = pd.read_csv(
                    file_path,
                    delimiter="|",  # or "," depending on your export logic
                    quotechar='"',
                    dtype=str  # optional: ensures all columns are read as strings
                )
                print(f"Loaded fallback vaccine_df from {file_name}")
            except Exception as e:
                print(f"Failed to load fallback file {file_name}: {e}")
                context.vaccine_df = pd.DataFrame()  # fallback to empty

            return None

        return func(*args, **kwargs)
    return wrapper

@given("batch file is created for below data as full dataset")
@ignore_if_local_run
def valid_batch_file_is_created_with_details(datatable, context):    
    build_dataFrame_using_datatable(datatable, context)        
    create_batch_file(context)

@when("same batch file is uploaded again in s3 bucket") 
@when("batch file is uploaded in s3 bucket")
@ignore_local_run_set_test_data
def batch_file_upload_in_s3_bucket(context):
    upload_file_to_S3(context)
    print(f"Batch file uploaded to S3: {context.filename}")
    fileIsMoved = wait_for_file_to_move_archive(context)
    assert fileIsMoved, f"File not found in archive after timeout"
    
@then("file will be moved to destination bucket and inf ack file will be created")
def file_will_be_moved_to_destination_bucket(context):
    context.fileContent = wait_and_read_ack_file(context, "ack")
    assert context.fileContent, f"File not found in destination bucket after timeout:  {context.forwarded_prefix}"
    
@then("inf ack file has success status for processed batch file")
def all_records_are_processed_successfully_in_the_inf_ack_file(context):  
    all_valid = validate_inf_ack_file(context)
    assert all_valid, "One or more records failed validation checks"
    
@then("bus ack file will be created")
def file_will_be_moved_to_destination_bucket(context):
    context.fileContent = wait_and_read_ack_file(context, "forwardedFile")
    assert context.fileContent, f"File not found in destination bucket after timeout: {context.forwarded_prefix}"
    
@then("bus ack will not have any entry of successfully processed records")
def all_records_are_processed_successfully_in_the_batch_file(context): 
    file_rows = read_and_validate_bus_ack_file_content(context) 
    all_valid = validate_bus_ack_file_for_successful_records(context, file_rows)
    assert all_valid, "One or more records failed validation checks"
    
@then("Audit table will have correct status, queue name and record count for the processed batch file")
def validate_imms_audit_table(context):
    table_query_response = fetch_batch_audit_table_detail(context.aws_profile_name, context.filename, context.S3_env)

    assert isinstance(table_query_response, list) and table_query_response, f"Item not found in response for filename: {context.filename}"
    item = table_query_response[0]
    validate_audit_table_record(context, item, "Processed")
    
@then("The delta table will be populated with the correct data for all created records in batch file")
def validate_imms_delta_table_for_created_records_in_batch_file(context):
    preload_delta_data(context)
    validate_imms_delta_table_for_newly_created_records_in_batch_file(context)
    
@then("The delta table will be populated with the correct data for all updated records in batch file")
def validate_imms_delta_table_for_updated_records(context):
    if context.delta_cache is None:
        preload_delta_data(context)
    validate_imms_delta_table_for_updated_records_in_batch_file(context)
    
@then("The delta table will be populated with the correct data for all deleted records in batch file")
def validate_imms_delta_table_for_deleted_records(context):
    if context.delta_cache is None:
        preload_delta_data(context)
    validate_imms_delta_table_for_deleted_records_in_batch_file(context)
            
@then(parsers.parse("The imms event table will be populated with the correct data for '{operation}' event for records in batch file"))
def validate_imms_event_table_for_all_records_in_batch_file(context, operation: Operation):
    mapping = ActionMap[operation.lower()]
    df = context.vaccine_df[context.vaccine_df["ACTION_FLAG"].str.lower() == mapping.action_flag.value.lower()]
            
    df["UNIQUE_ID_COMBINED"] = df["UNIQUE_ID_URI"].astype(str) + "#" + df["UNIQUE_ID"].astype(str)
    valid_rows = df[df["UNIQUE_ID_COMBINED"].notnull() & (df["UNIQUE_ID_COMBINED"] != "nan#nan")]

    for idx, row in valid_rows.iterrows():
        unique_id_combined = row["UNIQUE_ID_COMBINED"]
        batch_record = {k: normalize(v) for k, v in row.to_dict().items()}

        table_query_response = fetch_immunization_events_detail_by_IdentifierPK(
            context.aws_profile_name, unique_id_combined, context.S3_env
        )
        assert "Items" in table_query_response and table_query_response["Count"] > 0, \
        f"Item not found in response for unique_id_combined: {unique_id_combined}"

        item = table_query_response["Items"][0]

        df.at[idx, "IMMS_ID"]=  item.get("PK")
        context.ImmsID= item.get("PK").replace("Immunization#", "")
        update_imms_id_for_all_related_rows(context.vaccine_df, unique_id_combined, context.ImmsID)

        resource_json_str = item.get("Resource")
        assert resource_json_str, "Resource field missing in item."

        try:
            resource = json.loads(resource_json_str)
        except (TypeError, json.JSONDecodeError) as e:
            print(f"Failed to parse Resource from item: {e}")
            raise AssertionError("Failed to parse Resource from response item.")

        assert resource is not None, "Resource is None in the response"
        created_event = parse_imms_int_imms_event_response(resource)
        
        nhs_number = batch_record.get("NHS_NUMBER") or "TBC"
       
        fields_to_compare = [
            ("Operation", Operation[operation].value, item.get("Operation")),
            ("SupplierSystem", context.supplier_name, item.get("SupplierSystem")),
            ("PatientPK", f'Patient#{nhs_number}', item.get("PatientPK")),
            ("PatientSK", f"{context.vaccine_type.upper()}#{context.ImmsID}", item.get("PatientSK")),
            ("Version", int(context.expected_version), int(item.get("Version"))),
        ]
        
        for name, expected, actual in fields_to_compare:
            check.is_true(
                    expected == actual,
                    f"Expected {name}: {expected}, Actual {actual}"
                )
            
        validate_to_compare_batch_record_with_event_table_record(context, batch_record, created_event)
    
  
@then("all records are rejected in the bus ack file and no imms id is generated")
def all_record_are_rejected_for_given_field_name(context):
    file_rows = read_and_validate_bus_ack_file_content(context) 
    all_valid = validate_bus_ack_file_for_error(context, file_rows)
    assert all_valid, "One or more records failed validation checks"

def normalize(value):
    return "" if pd.isna(value) or value == "" else value

def create_batch_file(context, file_ext: str = "csv", fileName: str = None, delimiter: str = "|"):
    offset = datetime.now().astimezone().strftime("%z")[-2:]
    context.FileTimestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + offset    
    context.file_extension = file_ext

    timestamp_pattern = r'\d{8}T\d{8}'

    if not fileName:
        context.filename = generate_file_name(context)
    else:
        suffix = "" if re.search(timestamp_pattern, fileName) else f"_{context.FileTimestamp}"
        context.filename = f"{fileName}{suffix}.{context.file_extension}"        
    
    save_record_to_batch_files_directory(context, delimiter)

    print(f"Batch file created: {context.filename}")
    
def build_dataFrame_using_datatable(datatable, context):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    headers = datatable[0]
    rows = datatable[1:]

    table_list = [
        (row[headers.index("patient_id")], f"{row[headers.index('unique_id')]}-{timestamp}")
        for row in rows
    ]    
    records = []
    for patient_id, unique_id in table_list:  
        context.patient_id = patient_id
        record = build_batch_file(context, unique_id=unique_id)
        flat_record = record.dict()
        if "data" in flat_record:
            flat_record = flat_record["data"]
        records.append(flat_record)
    
    context.vaccine_df = pd.DataFrame(records)

def update_imms_id_for_all_related_rows(df, unique_id_combined, imms_id):
    mask = (df["UNIQUE_ID_URI"].astype(str) + "#" + df["UNIQUE_ID"].astype(str)) == unique_id_combined
    df.loc[mask, "IMMS_ID"] = imms_id
    
def preload_delta_data(context):
    df = context.vaccine_df

    check.is_true("IMMS_ID" in df.columns, "Column 'IMMS_ID' not found in vaccine_df")

    valid_rows = df[df["IMMS_ID"].notnull()]
    check.is_true(not valid_rows.empty, "No rows with non-null IMMS_ID found in vaccine_df")

    grouped = valid_rows.groupby("IMMS_ID")

    context.delta_cache = {}

    for imms_id, group in grouped:
        clean_id = imms_id.replace("Immunization#", "")
        delta_items = fetch_immunization_int_delta_detail_by_immsID(
            context.aws_profile_name,
            clean_id,
            context.S3_env
        )
        check.is_true(delta_items, f"No delta records returned for IMMS_ID: {clean_id}")

        context.delta_cache[clean_id] = {
            "rows": group,
            "delta_items": delta_items
        }
        
def validate_imms_delta_table_for_newly_created_records_in_batch_file(context):
    for clean_id, data in context.delta_cache.items():
        rows = data["rows"]
        delta_items = data["delta_items"]

        create_items = [i for i in delta_items if i.get("Operation") == "CREATE"]

        check.is_true(
            len(create_items) == 1,
            f"Expected exactly 1 CREATE record for IMMS_ID {clean_id}, found {len(create_items)}"
        )

        create_item = create_items[0]

        for _, row in rows[rows["ACTION_FLAG"] == "NEW"].iterrows():
            batch_record = {k: normalize(v) for k, v in row.to_dict().items()}

            validate_imms_delta_record_with_batch_record(
                context,
                batch_record,
                create_item,
                Operation.created.value,
                ActionFlag.created.value
            )
            
def validate_imms_delta_table_for_updated_records_in_batch_file(context):
    for clean_id, data in context.delta_cache.items():
        rows = data["rows"]
        delta_items = data["delta_items"]

        update_items = [i for i in delta_items if i.get("Operation") == "UPDATE"]
        check.is_true(update_items, f"No UPDATE records for IMMS_ID {clean_id}")
        updated_index = context.expected_version - 2  
        for _, row in rows[rows["ACTION_FLAG"] == "UPDATE"].iterrows():
            batch_record = {k: normalize(v) for k, v in row.to_dict().items()}
            item = update_items.pop(updated_index)

            validate_imms_delta_record_with_batch_record(
                context,
                batch_record,
                item,
                Operation.updated.value,
                ActionFlag.updated.value
            )
            
def validate_imms_delta_table_for_deleted_records_in_batch_file(context):
    for clean_id, data in context.delta_cache.items():
        rows = data["rows"]
        delta_items = data["delta_items"]

        delete_item = next(
            (i for i in delta_items if i.get("Operation") == "DELETE"),
            None
        )

        check.is_true(delete_item, f"No DELETE record for IMMS_ID {clean_id}")

        delete_rows = rows[rows["ACTION_FLAG"] == "DELETE"]

        check.is_true(
            len(delete_rows) == 1,
            f"Expected exactly 1 DELETE row in batch file for IMMS_ID {clean_id}, found {len(delete_rows)}"
        )

        row = delete_rows.iloc[0]
        batch_record = {k: normalize(v) for k, v in row.to_dict().items()}

        validate_imms_delta_record_with_batch_record(
            context,
            batch_record,
            delete_item,
            Operation.deleted.value,
            ActionFlag.deleted.value
        )