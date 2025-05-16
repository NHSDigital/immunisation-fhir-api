import boto3
import json
import os
import time
from datetime import datetime, timedelta
import uuid
import logging
from botocore.exceptions import ClientError
from log_firehose import FirehoseLogger
from Converter import Converter
from common.mappings import ActionFlag, Operation, EventName

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
firehose_logger = FirehoseLogger()


def send_message(record):
    # Create a message
    message_body = record
    try:
        sqs_client = boto3.client("sqs")
        sqs_client.send_message(QueueUrl=failure_queue_url, MessageBody=json.dumps(message_body))
        logger.info("Record saved successfully to the DLQ")
    except ClientError as e:
        logger.error(f"Error sending record to DLQ: {e}")

def get_vaccine_type(patientsk) -> str:
    parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
    return parsed[0]


def process_record(record, delta_table, log_data, firehose_log):
    """
    Processes a single record from the event.

    Args:
        record (dict): The DynamoDB stream record to process.
        delta_table (boto3.Table): The DynamoDB table resource.
        log_data (dict): Log data for the current record.
        firehose_log (dict): Firehose log data for the current record.

    Returns:
        bool: True if the record was processed successfully, False otherwise.
    """
    try:
        start = time.time()
        approximate_creation_time = datetime.utcfromtimestamp(record["dynamodb"]["ApproximateCreationDateTime"])
        expiry_time = approximate_creation_time + timedelta(days=30)
        expiry_time_epoch = int(expiry_time.timestamp())
        error_records = []
        response = str()
        imms_id = str()
        operation = str()

        if record["eventName"] != EventName.DELETE_PHYSICAL:
            new_image = record["dynamodb"]["NewImage"]
            imms_id = new_image["PK"]["S"].split("#")[1]
            vaccine_type = get_vaccine_type(new_image["PatientSK"]["S"])
            supplier_system = new_image["SupplierSystem"]["S"]

            if supplier_system not in ("DPSFULL", "DPSREDUCED"):
                operation = new_image["Operation"]["S"]
                action_flag = ActionFlag.CREATE if operation == Operation.CREATE else operation
                resource_json = json.loads(new_image["Resource"]["S"])
                FHIRConverter = Converter(json.dumps(resource_json))
                flat_json = FHIRConverter.runConversion(resource_json)  # Get the flat JSON
                error_records = FHIRConverter.getErrorRecords()
                flat_json["ACTION_FLAG"] = action_flag

                response = delta_table.put_item(
                    Item={
                        "PK": str(uuid.uuid4()),
                        "ImmsID": imms_id,
                        "Operation": operation,
                        "VaccineType": vaccine_type,
                        "SupplierSystem": supplier_system,
                        "DateTimeStamp": approximate_creation_time.isoformat(),
                        "Source": delta_source,
                        "Imms": flat_json,
                        "ExpiresAt": expiry_time_epoch,
                    }
                )
            else:
                operation_outcome = {
                    "statusCode": "200",
                    "statusDesc": "Record from DPS skipped",
                }
                log_data["operation_outcome"] = operation_outcome
                firehose_log["event"] = log_data
                firehose_logger.send_log(firehose_log)
                logger.info(f"Record from DPS skipped for {imms_id}")
                return True
        else:
            operation = Operation.DELETE_PHYSICAL
            new_image = record["dynamodb"]["Keys"]
            logger.info(f"Record to delta: {new_image}")
            imms_id = new_image["PK"]["S"].split("#")[1]

            response = delta_table.put_item(
                Item={
                    "PK": str(uuid.uuid4()),
                    "ImmsID": imms_id,
                    "Operation": Operation.DELETE_PHYSICAL,
                    "VaccineType": "default",
                    "SupplierSystem": "default",
                    "DateTimeStamp": approximate_creation_time.isoformat(),
                    "Source": delta_source,
                    "Imms": "",
                    "ExpiresAt": expiry_time_epoch,
                }
            )

        end = time.time()
        log_data["time_taken"] = f"{round(end - start, 5)}s"
        operation_outcome = {"record": imms_id, "operation_type": operation}

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            if error_records:
                log = f"Partial success: successfully synced into delta, but issues found within record {imms_id}"
                operation_outcome["statusCode"] = "207"
                operation_outcome["statusDesc"] = (
                    f"Partial success: successfully synced into delta, but issues found within record {json.dumps(error_records)}"
                )
            else:
                log = f"Record Successfully created for {imms_id}"
                operation_outcome["statusCode"] = "200"
                operation_outcome["statusDesc"] = "Successfully synched into delta"
            logger.info(log)
        else:
            log = f"Record NOT created for {imms_id}"
            operation_outcome["statusCode"] = "500"
            operation_outcome["statusDesc"] = "Exception"
            logger.warning(log)
            return False

        log_data["operation_outcome"] = operation_outcome
        firehose_log["event"] = log_data
        firehose_logger.send_log(firehose_log)
        return True

    except Exception as e:
        logger.exception(f"Error processing record: {e}")
        return False


def handler(event, context):
    ret = True
    logger.info("Starting Delta Handler")
    log_data = dict()
    firehose_log = dict()
    log_data["function_name"] = "delta_sync"
    try:
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        delta_table = dynamodb.Table(delta_table_name)
        for record in event["Records"]:
            log_data["date_time"] = str(datetime.now())

            # Process each record
            result = process_record(record, delta_table, log_data, firehose_log)
            if not result:
                ret = False

    except Exception as e:
        ret = False
        operation_outcome = {
            "statusCode": "500",
            "statusDesc": "Exception",
            "diagnostics": f"Delta Lambda failure: Incorrect invocation of Lambda"
        }
        logger.exception(operation_outcome["diagnostics"])
        send_message(event)  # Send failed records to DLQ
        log_data["operation_outcome"] = operation_outcome
        firehose_log["event"] = log_data
        firehose_logger.send_log(firehose_log)
    return ret
