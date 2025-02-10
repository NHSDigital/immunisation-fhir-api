"""Values for use in ack_processor tests"""

import json
from datetime import datetime


class DefaultValues:
    """Class to hold default values for tests"""

    message_id = "test_file_id"
    row_id = "test_file_id#1"
    local_id = "test_system_uri^testabc"
    imms_id = "test_imms_id"
    operation_requested = "CREATE"
    created_at_formatted_string = "20211120T12000000"


class DiagnosticsDictionaries:
    """Example diagnostics dictionaries which may be received from the record forwarder"""

    UNIQUE_ID_MISSING = {
        "error_type": "MissingUniqueID",
        "statusCode": 400,
        "error_message": "UNIQUE_ID or UNIQUE_ID_URI is missing",
    }

    NO_PERMISSIONS = {
        "error_type": "NoPermissions",
        "statusCode": 403,
        "error_message": "No permissions for requested operation",
    }

    INVALID_ACTION_FLAG = {
        "error_type": "InvalidActionFlag",
        "statusCode": 400,
        "error_message": "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'",
    }

    CUSTOM_VALIDATION_ERROR = {
        "error_type": "CustomValidationError",
        "statusCode": 400,
        "error_message": "Custom validation error",
    }

    IDENTIFIER_DUPLICATION_ERROR = {
        "error_type": "IdentifierDuplicationError",
        "statusCode": 422,
        "error_message": "Identifier duplication error",
    }

    RESOURCE_NOT_FOUND_ERROR = {
        "error_type": "ResourceNotFoundError",
        "statusCode": 404,
        "error_message": "Resource not found error",
    }

    RESOURCE_FOUND_ERROR = {
        "error_type": "ResourceFoundError",
        "statusCode": 409,
        "error_message": "Resource found error",
    }

    MESSAGE_NOT_SUCCESSFUL_ERROR = {
        "error_type": "MessageNotSuccessfulError",
        "statusCode": 500,
        "error_message": "Message not successful error",
    }

    UNHANDLED_ERROR = {
        "error_type": "UnhandledResponseError",
        "statusCode": 500,
        "error_message": "An unhandled error occurred during batch processing",
    }


class MessageDetails:
    """
    Class to create and hold values for a mock message, based on the vaccine type, supplier and ods code.
    NOTE: Supplier and ODS code are hardcoded rather than mapped, for testing purposes.
    """

    def __init__(
        self,
        vaccine_type: str,
        supplier: str,
        ods_code: str,
        operation_requested: str = DefaultValues.operation_requested,
        message_id: str = DefaultValues.message_id,
        row_id: str = DefaultValues.row_id,
        local_id: str = DefaultValues.local_id,
        imms_id: str = DefaultValues.imms_id,
        created_at_formatted_string: str = DefaultValues.created_at_formatted_string,
    ):
        self.name = f"{vaccine_type.upper()}/ {supplier.upper()} {operation_requested} message"
        self.file_key = f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv"
        self.temp_ack_file_key = (
            f"TempAck/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_BusAck_20211120T12000000.csv"
        )
        self.archive_ack_file_key = (
            f"forwardedFile/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_BusAck_20211120T12000000.csv"
        )
        self.vaccine_type = vaccine_type
        self.ods_code = ods_code
        self.supplier = supplier
        self.operation_requested = operation_requested
        self.message_id = message_id
        self.row_id = row_id
        self.local_id = local_id
        self.imms_id = imms_id
        self.created_at_formatted_string = created_at_formatted_string

        self.queue_name = f"{supplier}_{vaccine_type}"

        self.base_message = {
            "file_key": self.file_key,
            "supplier": self.supplier,
            "vaccine_type": self.vaccine_type,
            "created_at_formatted_string": self.created_at_formatted_string,
            "row_id": self.row_id,
            "local_id": self.local_id,
            "operation_requested": self.operation_requested,
        }

        self.success_message = {**self.base_message, "imms_id": imms_id}

        self.failure_message = {**self.base_message, "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS}


class MockMessageDetails:
    """Class containing mock message details for use in tests"""

    rsv_ravs = MessageDetails("RSV", "RAVS", "X26")
    rsv_emis = MessageDetails("RSV", "EMIS", "8HK48")
    flu_emis = MessageDetails("FLU", "EMIS", "YGM41")


# Mock message details are used as the default message details for the tests
MOCK_MESSAGE_DETAILS = MockMessageDetails.rsv_ravs

EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS = {
    "statusCode": 200,
    "body": json.dumps("Lambda function executed successfully!"),
}


class ValidValues:
    """Valid values for use in tests"""

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

    mock_message_expected_log_value = {
        "function_name": "ack_processor_convert_message_to_ack_row",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "success",
        "supplier": MOCK_MESSAGE_DETAILS.supplier,
        "file_key": MOCK_MESSAGE_DETAILS.file_key,
        "vaccine_type": MOCK_MESSAGE_DETAILS.vaccine_type,
        "message_id": MOCK_MESSAGE_DETAILS.row_id,
        "operation_requested": "CREATE",
        "time_taken": "1.0s",
        "local_id": MOCK_MESSAGE_DETAILS.local_id,
        "statusCode": 200,
        "diagnostics": "Operation completed successfully",
    }

    ack_data_success_dict = {
        "MESSAGE_HEADER_ID": DefaultValues.row_id,
        "HEADER_RESPONSE_CODE": "OK",
        "ISSUE_SEVERITY": "Information",
        "ISSUE_CODE": "OK",
        "ISSUE_DETAILS_CODE": "30001",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30001",
        "RESPONSE_DISPLAY": "Success",
        "RECEIVED_TIME": DefaultValues.created_at_formatted_string,
        "MAILBOX_FROM": "",
        "LOCAL_ID": DefaultValues.local_id,
        "IMMS_ID": DefaultValues.imms_id,
        "OPERATION_OUTCOME": "",
        "MESSAGE_DELIVERY": True,
    }

    ack_data_failure_dict = {
        "MESSAGE_HEADER_ID": DefaultValues.row_id,
        "HEADER_RESPONSE_CODE": "Fatal Error",
        "ISSUE_SEVERITY": "Fatal",
        "ISSUE_CODE": "Fatal Error",
        "ISSUE_DETAILS_CODE": "30002",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30002",
        "RESPONSE_DISPLAY": "Business Level Response Value - Processing Error",
        "RECEIVED_TIME": DefaultValues.created_at_formatted_string,
        "MAILBOX_FROM": "",
        "LOCAL_ID": DefaultValues.local_id,
        "IMMS_ID": "",
        "OPERATION_OUTCOME": "DIAGNOSTICS",
        "MESSAGE_DELIVERY": False,
    }

    lambda_handler_success_expected_log = {
        "function_name": "ack_processor_lambda_handler",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "success",
        "statusCode": 200,
        "message": "Lambda function executed successfully!",
    }

    lambda_handler_failure_expected_log = {
        "function_name": "ack_processor_lambda_handler",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "fail",
        "statusCode": 500,
        "diagnostics": "DIAGNOSTICS MESSAGE",
    }

    ack_headers = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
        "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|IMMS_ID|OPERATION_OUTCOME"
        "|MESSAGE_DELIVERY\n"
    )


class InvalidValues:
    """Invalid values for use in tests"""

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

    Logging_with_no_values = {
        "function_name": "ack_processor_convert_message_to_ack_row",
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
        "diagnostics": "An unhandled error occurred during batch processing",
    }
