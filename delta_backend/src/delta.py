import boto3
import json
import os
import time
from datetime import datetime, timedelta
import uuid
import logging
from botocore.exceptions import ClientError
from log_firehose import FirehoseLogger
from helpers.db_processor import DbProcessor
from helpers.mappings import OperationName, EventName, ActionFlag
from helpers.record_processor import RecordProcessor
from helpers.sqs_utils import send_message

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
firehose_logger = FirehoseLogger()


# def send_message(record):
#     # Create a message
#     message_body = record
#     # Use boto3 to interact with SQS
#     sqs_client = boto3.client("sqs")
#     try:
#         # Send the record to the queue
#         print(f"Sending record to DLQ: {message_body}")
#         sqs_client.send_message(QueueUrl=failure_queue_url, MessageBody=json.dumps(message_body))
#         logger.info("Record saved successfully to the DLQ")
#     except ClientError as e:
#         logger.error(f"Error sending record to DLQ: {e}")

def get_vaccine_type(patientsk) -> str:
    parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
    return parsed[0]

def handler(event, context):
    logger.info("Starting Delta Handler")
    log_data = dict()
    firehose_log = dict()
    operation_outcome = dict()
    log_data["function_name"] = "delta_sync"
    intrusion_check = True
    try:
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        delta_table = dynamodb.Table(delta_table_name)
        db_processor = DbProcessor(delta_table, delta_source, logger)
        record_processor = RecordProcessor(delta_table,
                                           delta_source,
                                           log_data,
                                           db_processor,
                                           firehose_logger,
                                           firehose_log,
                                           logger)
        for record in event["Records"]:
            record_processor.process_record(record)


    except Exception as e:
        operation_outcome["statusCode"] = "500"
        operation_outcome["statusDesc"] = "Exception"
        if intrusion_check:
            operation_outcome["diagnostics"] = "Incorrect invocation of Lambda"
            logger.exception("Incorrect invocation of Lambda")
        else:
            operation_outcome["diagnostics"] = f"Delta Lambda failure: {e}"
            logger.exception(f"Delta Lambda failure: {e}")
            send_message(event)  # Send failed records to DLQ
        log_data["operation_outcome"] = operation_outcome
        firehose_log["event"] = log_data
        firehose_logger.send_log(firehose_log)
        return {
            "statusCode": 500,
            "body": "Records not processed",
        }

