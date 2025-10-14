import decimal
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from common.mappings import ActionFlag, EventName, Operation
from converter import Converter
from log_firehose import FirehoseLogger

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
delta_ttl_days = os.environ["DELTA_TTL_DAYS"]
region_name = "eu-west-2"
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
firehose_logger = FirehoseLogger()

delta_table = None


def get_delta_table():
    """
    Initialize the DynamoDB table resource with exception handling.
    """
    global delta_table
    if not delta_table:
        try:
            logger.info("Initializing Delta Table")
            dynamodb = boto3.resource("dynamodb", region_name)
            delta_table = dynamodb.Table(delta_table_name)
        except Exception as e:
            logger.error(f"Error initializing Delta Table: {e}")
            delta_table = None
    return delta_table


sqs_client = None


def get_sqs_client():
    """
    Initialize the SQS client with exception handling.
    """
    global sqs_client
    if not sqs_client:
        try:
            logger.info("Initializing SQS Client")
            sqs_client = boto3.client("sqs", region_name)
        except Exception:
            logger.exception("Error initializing SQS Client")
            sqs_client = None
    return sqs_client


def send_message(record, queue_url=failure_queue_url):
    # Create a message
    message_body = record
    try:
        # Send the record to the queue
        get_sqs_client().send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
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


def send_firehose(log_data):
    try:
        firehose_log = {"event": log_data}
        firehose_logger.send_log(firehose_log)
    except Exception:
        logger.exception("Error sending log to Firehose")


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


def handler(event, _context):
    overall_success = True
    logger.info("Starting Delta Handler")
    try:
        for record in event["Records"]:
            datetime_str = datetime.now().isoformat()
            start = time.time()
            success, operation_outcome = process_record(record)
            overall_success = overall_success and success
            end = time.time()
            send_firehose(
                {
                    "function_name": "delta_sync",
                    "operation_outcome": operation_outcome,
                    "date_time": datetime_str,
                    "time_taken": f"{round(end - start, 5)}s",
                }
            )
    except Exception:
        overall_success = False
        operation_outcome = {
            "statusCode": "500",
            "statusDesc": "Exception",
            "diagnostics": "Delta Lambda failure: Incorrect invocation of Lambda",
        }
        logger.exception(operation_outcome["diagnostics"])
        send_message(event)  # Send failed records to DLQ
        send_firehose({"function_name": "delta_sync", "operation_outcome": operation_outcome})

    if not overall_success:
        send_message(event)

    return overall_success
