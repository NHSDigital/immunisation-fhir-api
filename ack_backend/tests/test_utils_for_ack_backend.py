"""Values for use in ack_processor tests"""

from datetime import datetime

REGION_NAME = "eu-west-2"


class BucketNames:
    """Bucket Names for testing"""

    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"
    MOCK_FIREHOSE = "mock-firehose-bucket"


class Firehose:
    """Class containing Firehose values for use in tests"""

    STREAM_NAME = "immunisation-fhir-api-internal-dev-splunk-firehose"


MOCK_ENVIRONMENT_DICT = {
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "FIREHOSE_STREAM_NAME": Firehose.STREAM_NAME,
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
    "ENVIRONMENT": "internal-dev",
}


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


class ValidValues:
    """Logging instances which are both valid and current"""

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

    EMIS_ack_processor_input = {
        "file_key": "RSV_Vaccinations_v5_YGM41_20240905T13005922",
        "row_id": "456",
        "local_id": "local_456",
        "operation_requested": "create",
        "imms_id": "4567",
        "created_at_formatted_string": "1223-12-232",
        "supplier": "EMIS",
        "vaccine_type": "RSV",
    }
    DPSFULL_ack_processor_input = {
        "file_key": "RSV_Vaccinations_v5_DPSFULL_20240905T13005922",
        "row_id": "123",
        "local_id": "local_123",
        "operation_requested": "create",
        "imms_id": "1232",
        "created_at_formatted_string": "1223-12-232",
        "supplier": "DPSFULL",
        "vaccine_type": "RSV",
    }

    EMIS_ack_processor_input_diagnostics = {
        "file_key": "RSV_Vaccinations_v5_YGM41_20240905T13005922",
        "row_id": "456",
        "local_id": "local_456",
        "operation_requested": "create",
        "imms_id": "4567",
        "created_at_formatted_string": "1223-12-232",
        "diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR,
        "supplier": "EMIS",
        "vaccine_type": "RSV",
    }

    DPSFULL_ack_processor_input_diagnostics = {
        "file_key": "RSV_Vaccinations_v5_DPSFULL_20240905T13005922",
        "row_id": "123",
        "local_id": "local_123",
        "operation_requested": "create",
        "imms_id": "1232",
        "created_at_formatted_string": "1223-12-232",
        "diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR,
        "supplier": "DPSFULL",
        "vaccine_type": "RSV",
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
        "function_name": "ack_processor_convert_message_to_ack_row",
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
        "IMMS_ID": "",
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

    ack_headers = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
        "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|IMMS_ID|OPERATION_OUTCOME"
        "|MESSAGE_DELIVERY\n"
    )


class InvalidValues:

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


class GenericSetUp:
    """
    Performs generic setup of mock resources:
    * If s3_client is provided, creates source, destination and firehose buckets (firehose bucket is used for testing
        only)
    * If firehose_client is provided, creates a firehose delivery stream
    """

    def __init__(self, s3_client=None, firehose_client=None):

        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION, BucketNames.MOCK_FIREHOSE]:
                s3_client.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME}
                )

        if firehose_client:
            firehose_client.create_delivery_stream(
                DeliveryStreamName=Firehose.STREAM_NAME,
                DeliveryStreamType="DirectPut",
                S3DestinationConfiguration={
                    "RoleARN": "arn:aws:iam::123456789012:role/mock-role",
                    "BucketARN": "arn:aws:s3:::" + BucketNames.MOCK_FIREHOSE,
                    "Prefix": "firehose-backup/",
                },
            )


class GenericTearDown:
    """Performs generic tear down of mock resources"""

    def __init__(self, s3_client=None, firehose_client=None):

        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION, BucketNames.MOCK_FIREHOSE]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(DeliveryStreamName=Firehose.STREAM_NAME)


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

        self.message = {
            "file_key": self.file_key,
            "supplier": self.supplier,
            "vaccine_type": self.vaccine_type,
            "created_at_formatted_string": self.created_at_formatted_string,
            "row_id": row_id,
            "local_id": local_id,
            "imms_id": imms_id,
            "operation_requested": operation_requested,
        }


class MockMessageDetails:
    """Class containing mock message details for use in tests"""

    rsv_ravs = MessageDetails("RSV", "RAVS", "X26")
    rsv_emis = MessageDetails("RSV", "EMIS", "8HK48")
    flu_emis = MessageDetails("FLU", "EMIS", "YGM41")
