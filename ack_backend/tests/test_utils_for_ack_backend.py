"""Values for use in ack_processor tests"""

from datetime import datetime

SOURCE_BUCKET_NAME = "immunisation-batch-internal-test-data-sources"
DESTINATION_BUCKET_NAME = "immunisation-batch-internal-test-data-destinations"
CONFIG_BUCKET_NAME = "immunisation-batch-internal-dev-configs"
STREAM_NAME = "imms-batch-internal-dev-processingdata-stream"
CREATED_AT_FORMATTED_STRING = "20241115T13435500"
IMMS_ID = "Immunization#932796c8-fd20-4d31-a4d7-e9613de70ad6"


AWS_REGION = "eu-west-2"
STATIC_DATETIME = datetime(2021, 11, 20, 12, 0, 0)


class ValidValues:
    """Logging instances which are both valid and current"""

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)
    local_id = "111^222"
    imms_id = "TEST_IMMS_ID"

    EMIS_ack_processor_input = {
        "file_key": "RSV_Vaccinations_v5_YGM41_20240905T13005922",
        "row_id": "456",
        "local_id": "local_456",
        "action_flag": "create",
        "imms_id": "4567",
        "created_at_formatted_string": "1223-12-232",
    }
    DPSFULL_ack_processor_input = {
        "file_key": "RSV_Vaccinations_v5_DPSFULL_20240905T13005922",
        "row_id": "123",
        "local_id": "local_123",
        "action_flag": "create",
        "imms_id": "1232",
        "created_at_formatted_string": "1223-12-232",
    }

    EMIS_ack_processor_input_diagnostics = {
        "file_key": "RSV_Vaccinations_v5_YGM41_20240905T13005922",
        "row_id": "456",
        "local_id": "local_456",
        "action_flag": "create",
        "imms_id": "4567",
        "created_at_formatted_string": "1223-12-232",
        "diagnostics": "Immunization resource does not exist",
    }

    DPSFULL_ack_processor_input_diagnostics = {
        "file_key": "RSV_Vaccinations_v5_DPSFULL_20240905T13005922",
        "row_id": "123",
        "local_id": "local_123",
        "action_flag": "create",
        "imms_id": "1232",
        "created_at_formatted_string": "1223-12-232",
        "diagnostics": "Immunization resource does not exist",
    }

    EMIS_expected_log_value = {
        "function_name": "ack_processor_lambda_handler",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "success",
        "supplier": "EMIS",
        "file_key": "RSV_Vaccinations_v5_YGM41_20240905T13005922",
        "vaccine_type": "RSV",
        "message_id": "456",
        "operation_requested": "create",
        "time_taken": "3.0s",
        "local_id": "local_456",
        "statusCode": 200,
        "diagnostics": "Operation completed successfully",
    }

    DPSFULL_expected_log_value = {
        "function_name": "ack_processor_lambda_handler",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "success",
        "supplier": "DPSFULL",
        "file_key": "RSV_Vaccinations_v5_DPSFULL_20240905T13005922",
        "vaccine_type": "RSV",
        "message_id": "123",
        "operation_requested": "create",
        "time_taken": "1.0s",
        "local_id": "local_123",
        "statusCode": 200,
        "diagnostics": "Operation completed successfully",
    }

    create_ack_data_successful_row = {
        "MESSAGE_HEADER_ID": "123^1",
        "HEADER_RESPONSE_CODE": "OK",
        "ISSUE_SEVERITY": "Information",
        "ISSUE_CODE": "OK",
        "ISSUE_DETAILS_CODE": "30001",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30001",
        "RESPONSE_DISPLAY": "Success",
        "RECEIVED_TIME": CREATED_AT_FORMATTED_STRING,
        "MAILBOX_FROM": "",
        "LOCAL_ID": local_id,
        "IMMS_ID": "",
        "OPERATION_OUTCOME": "",
        "MESSAGE_DELIVERY": True,
    }

    create_ack_data_failure_row = {
        "MESSAGE_HEADER_ID": "123^1",
        "HEADER_RESPONSE_CODE": "Fatal Error",
        "ISSUE_SEVERITY": "Fatal",
        "ISSUE_CODE": "Fatal Error",
        "ISSUE_DETAILS_CODE": "30002",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30002",
        "RESPONSE_DISPLAY": "Business Level Response Value - Processing Error",
        "RECEIVED_TIME": CREATED_AT_FORMATTED_STRING,
        "MAILBOX_FROM": "",
        "LOCAL_ID": local_id,
        "IMMS_ID": "",
        "OPERATION_OUTCOME": "Error_value",
        "MESSAGE_DELIVERY": False,
    }

    update_ack_file_successful_row_no_immsid = (
        f"123^1|OK|Information|OK|30001|Business|30001|Success|{CREATED_AT_FORMATTED_STRING}||{local_id}|||True\n"
    )

    update_ack_file_failure_row_no_immsid = (
        "123^1|Fatal Error|Fatal|Fatal Error|30002|Business|30002|"
        f"Business Level Response Value - Processing Error|{CREATED_AT_FORMATTED_STRING}|"
        f"|{local_id}||Error_value|False\n"
    )

    update_ack_file_successful_row_immsid = (
        "123^1|OK|Information|OK|30001|Business|30001|Success"
        f"|{CREATED_AT_FORMATTED_STRING}||{local_id}|{imms_id}||True\n"
    )

    update_ack_file_failure_row_immsid = (
        "123^1|Fatal Error|Fatal|Fatal Error|30002|Business|30002|Business Level Response Value - Processing Error"
        f"|{CREATED_AT_FORMATTED_STRING}||{local_id}|{imms_id}|Error_value|False\n"
    )

    existing_ack_file_content = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
        "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|IMMS_ID|OPERATION_OUTCOME"
        "|MESSAGE_DELIVERY\n123^5|OK|Information|OK|30001|Business|30001|Success|20241115T13435500||999^TEST|||True\n"
    )

    test_ack_header = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
        "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|IMMS_ID|OPERATION_OUTCOME"
        "|MESSAGE_DELIVERY\n"
    )


class InvalidValues:

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

    Logging_with_no_values = {
        "function_name": "ack_processor_lambda_handler",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "fail",
        "supplier": "unknown",
        "file_key": "file_key_missing",
        "vaccine_type": "unknown",
        "message_id": "unknown",
        "operation_requested": "unknown",
        "time_taken": "1.0s",
        "local_id": "unknown",
        "statusCode": 500,
        "diagnostics": "An unhandled error happened during batch processing",
    }
