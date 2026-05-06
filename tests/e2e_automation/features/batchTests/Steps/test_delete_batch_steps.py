import pandas as pd
from pytest_bdd import given, scenarios, then, when
from src.objectModels.batch.batch_file_builder import build_batch_file

from features.APITests.steps.common_steps import (
    validate_imms_event_table_by_operation,
    validVaccinationRecordIsCreated,
)
from features.APITests.steps.test_create_steps import (
    validate_imms_delta_table_by_ImmsID,
)
from features.APITests.steps.test_delete_steps import (
    validate_imms_delta_table_by_deleted_ImmsID,
)

from .batch_common_steps import (
    build_batch_row_from_api_object,
    build_dataFrame_using_datatable,
    create_batch_file,
    ignore_if_local_run,
)

scenarios("batchTests/delete_batch.feature")


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
    df = pd.DataFrame([record.dict()])

    batch_fields = build_batch_row_from_api_object(context, "DELETE")
    df.loc[0, list(batch_fields.keys())] = list(batch_fields.values())

    context.vaccine_df = df
    create_batch_file(context)
    context.vaccine_df.loc[0, "IMMS_ID"] = context.ImmsID


@then("The delta and imms event table will be populated with the correct data for api created event")
@given("The delta and imms event table will be populated with the correct data for api created event")
def validate_imms_delta_table_for_api_created_event(context):
    validate_imms_event_table_by_operation(context, "created")
    validate_imms_delta_table_by_ImmsID(context)


@when("Delete above vaccination record is made through batch file upload with mandatory field missing")
def upload_batch_file_to_s3_for_update_with_mandatory_field_missing(context):
    record = build_batch_file(context)
    df = pd.DataFrame([record.dict()])

    batch_fields = build_batch_row_from_api_object(context, "DELETE")
    batch_fields["PERSON_DOB"] = ""
    df.loc[0, list(batch_fields.keys())] = list(batch_fields.values())

    context.vaccine_df = df
    create_batch_file(context)
    context.vaccine_df.loc[0, "IMMS_ID"] = context.ImmsID


@then("The imms event table status will be updated to delete and no change to record detail")
def validate_imms_event_table_for_delete_event(context):
    validate_imms_event_table_by_operation(context, "deleted")


@then("The delta table will have delete entry with no change to record detail")
def validate_delta_table_for_delete_event(context):
    validate_imms_delta_table_by_deleted_ImmsID(context)


@given(
    "batch file is created for below data as full dataset and each record delete and the followed with create/update action flag"
)
@ignore_if_local_run
def valid_batch_file_is_created_with_delete_action_flag_and_create_update_action_flag(datatable, context):
    build_dataFrame_using_datatable(datatable, context)
    df_new = context.vaccine_df.copy()
    df_update = df_new.copy()
    df_update["ACTION_FLAG"] = "DELETE"
    df_reinstated = df_new.copy()
    df_reinstated.iloc[0, df_reinstated.columns.get_loc("ACTION_FLAG")] = "NEW"
    df_reinstated.iloc[1, df_reinstated.columns.get_loc("ACTION_FLAG")] = "UPDATE"
    context.vaccine_df = pd.concat([df_new, df_update, df_reinstated], ignore_index=True)
    create_batch_file(context)
    context.expected_version = 2
