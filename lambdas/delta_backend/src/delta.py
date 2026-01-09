import decimal
import json
import os
import time
from datetime import UTC, datetime, timedelta

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from common.aws_dynamodb import get_dynamodb_table
from common.clients import STREAM_NAME, get_sqs_client, logger
from common.log_firehose import send_log_to_firehose
from converter import Converter
from mappings import ActionFlag, EventName, Operation

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
delta_ttl_days = os.environ["DELTA_TTL_DAYS"]
region_name = "eu-west-2"

delta_table = None


def get_delta_table():
    """
    Initialize the DynamoDB table resource with exception handling.
    """
    global delta_table
    if not delta_table:
        try:
            logger.info("Initializing Delta Table")
            delta_table = get_dynamodb_table(delta_table_name)
        except Exception as e:
            logger.error(f"Error initializing Delta Table: {e}")
            delta_table = None
    return delta_table


def send_record_to_dlq(record: dict) -> None:
    try:
        get_sqs_client().send_message(QueueUrl=failure_queue_url, MessageBody=json.dumps(record))
        logger.info("Record saved successfully to the DLQ")
    except Exception:
        logger.exception("Error sending record to DLQ")


def get_vaccine_type(patient_sort_key: str) -> str:
    vaccine_type = patient_sort_key.split("#")[0]
    return str.strip(str.lower(vaccine_type))


def get_imms_id(primary_key: str) -> str:
    return primary_key.split("#")[1]


def get_creation_and_expiry_times(creation_timestamp: float) -> (str, int):
    creation_datetime = datetime.fromtimestamp(creation_timestamp, UTC)
    expiry_datetime = creation_datetime + timedelta(days=int(delta_ttl_days))
    expiry_timestamp = int(expiry_datetime.timestamp())
    return creation_datetime.isoformat(), expiry_timestamp


def handle_dynamodb_response(response, error_records):
    match response:
        case {"ResponseMetadata": {"HTTPStatusCode": 200}} if error_records:
            logger.warning(
                "Partial success: successfully synced into delta, "
                f"but issues found within record: {json.dumps(error_records)}"
            )
            return True, {
                "statusCode": "207",
                "statusDesc": "Partial success: successfully synced into delta, but issues found within record",
                "diagnostics": error_records,
            }
        case {"ResponseMetadata": {"HTTPStatusCode": 200}}:
            logger.info("Successfully synched into delta")
            return True, {
                "statusCode": "200",
                "statusDesc": "Successfully synched into delta",
            }
        case _:
            logger.error(f"Failure response from DynamoDB: {response}")
            return False, {
                "statusCode": "500",
                "statusDesc": "Failure response from DynamoDB",
                "diagnostics": response,
            }


def handle_exception_response(response):
    match response:
        case ClientError(response={"Error": {"Code": "ConditionalCheckFailedException"}}):
            logger.info("Skipped record already present in delta")
            return True, {
                "statusCode": "200",
                "statusDesc": "Skipped record already present in delta",
            }
        case _:
            logger.exception("Exception during processing")
            return False, {
                "statusCode": "500",
                "statusDesc": "Exception",
                "diagnostics": response,
            }


def process_remove(record):
    event_id = record["eventID"]
    primary_key = record["dynamodb"]["Keys"]["PK"]["S"]
    imms_id = get_imms_id(primary_key)
    operation = Operation.DELETE_PHYSICAL
    creation_timestamp = record["dynamodb"]["ApproximateCreationDateTime"]
    creation_datetime_str, expiry_timestamp = get_creation_and_expiry_times(creation_timestamp)
    operation_outcome = {"operation_type": operation, "record": imms_id}
    try:
        response = get_delta_table().put_item(
            Item={
                "PK": event_id,
                "ImmsID": imms_id,
                "Operation": operation,
                "VaccineType": "default",
                "SupplierSystem": "default",
                "DateTimeStamp": creation_datetime_str,
                "Source": delta_source,
                "Imms": "",
                "ExpiresAt": expiry_timestamp,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        success, extra_log_fields = handle_dynamodb_response(response, None)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome
    except Exception as e:
        success, extra_log_fields = handle_exception_response(e)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome


def process_skip(record):
    primary_key = record["dynamodb"]["NewImage"]["PK"]["S"]
    imms_id = get_imms_id(primary_key)
    logger.info("Record from DPS skipped")
    return True, {
        "record": imms_id,
        "statusCode": "200",
        "statusDesc": "Record from DPS skipped",
    }


def process_create_update_delete(record):
    event_id = record["eventID"]
    new_image = record["dynamodb"]["NewImage"]
    primary_key = new_image["PK"]["S"]
    imms_id = get_imms_id(primary_key)
    operation = new_image["Operation"]["S"]
    vaccine_type = get_vaccine_type(new_image["PatientSK"]["S"])
    supplier_system = new_image["SupplierSystem"]["S"]
    creation_timestamp = record["dynamodb"]["ApproximateCreationDateTime"]
    creation_datetime_str, expiry_timestamp = get_creation_and_expiry_times(creation_timestamp)
    action_flag = ActionFlag.CREATE if operation == Operation.CREATE else operation
    resource_json = json.loads(new_image["Resource"]["S"], parse_float=decimal.Decimal)
    fhir_converter = Converter(resource_json, action_flag=action_flag)
    flat_json = fhir_converter.run_conversion()
    error_records = fhir_converter.get_error_records()
    operation_outcome = {"record": imms_id, "operation_type": operation}

    try:
        response = get_delta_table().put_item(
            Item={
                "PK": event_id,
                "ImmsID": imms_id,
                "Operation": operation,
                "VaccineType": vaccine_type,
                "SupplierSystem": supplier_system,
                "DateTimeStamp": creation_datetime_str,
                "Source": delta_source,
                "Imms": flat_json,
                "ExpiresAt": expiry_timestamp,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        success, extra_log_fields = handle_dynamodb_response(response, error_records)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome
    except Exception as e:
        success, extra_log_fields = handle_exception_response(e)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome


def process_record(record):
    try:
        if record["eventName"] == EventName.DELETE_PHYSICAL:
            return process_remove(record)

        supplier_system = record["dynamodb"]["NewImage"]["SupplierSystem"]["S"]
        if supplier_system in ("DPSFULL", "DPSREDUCED"):
            return process_skip(record)

        return process_create_update_delete(record)
    except Exception as e:
        logger.exception("Exception during processing")
        return False, {"statusCode": "500", "statusDesc": "Exception", "diagnostics": e}


def handler(event, _context) -> bool:
    logger.info("Starting Delta Handler")

    for record in event["Records"]:
        record_ingestion_datetime = datetime.now().isoformat()
        record_processing_start = time.time()
        success, operation_outcome = process_record(record)
        record_processing_end = time.time()
        log_data = {
            "function_name": "delta_sync",
            "operation_outcome": operation_outcome,
            "date_time": record_ingestion_datetime,
            "time_taken": f"{round(record_processing_end - record_processing_start, 5)}s",
        }
        send_log_to_firehose(STREAM_NAME, log_data)

        if not success:
            send_record_to_dlq(record)

    return True
