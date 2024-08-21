import boto3
import json
import os
import time
from datetime import datetime, timedelta
import uuid
import logging
from botocore.exceptions import ClientError
from log_firehose import FirehoseLogger
from convert_flat_json import convert_to_flat_json

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
    # Use boto3 to interact with SQS
    sqs_client = boto3.client("sqs")
    try:
        # Send the record to the queue
        sqs_client.send_message(
            QueueUrl=failure_queue_url, MessageBody=json.dumps(message_body)
        )
        print("Record saved successfully to the DLQ")
    except ClientError as e:
        print(f"Error sending record to DLQ: {e}")

def get_vaccine_type( patientsk ) -> str:
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
        dynamodb = boto3.resource("dynamodb")
        delta_table = dynamodb.Table(delta_table_name)

        # Converting ApproximateCreationDateTime directly to string will give Unix timestamp
        # I am converting it to isofformat for filtering purpose. This can be changed accordingly

        for record in event["Records"]:
            start = time.time()
            log_data["date_time"] = str(datetime.now())
            intrusion_check = False
            approximate_creation_time = datetime.utcfromtimestamp(
                record["dynamodb"]["ApproximateCreationDateTime"]
            )
            expiry_time = approximate_creation_time + timedelta(days=30)
            expiry_time_epoch = int(expiry_time.timestamp())
            response = str()
            imms_id = str()
            operation = str()
            if record["eventName"] != "REMOVE":
                new_image = record["dynamodb"]["NewImage"]
                print(f"new_image:{new_image}")
                imms_id = new_image["PK"]["S"].split("#")[1]
                vaccine_type = get_vaccine_type(new_image["PatientSK"]["S"])
                supplier_system = new_image["IdentifierPK"]["S"]
                if supplier_system != "DPS":
                    operation = new_image["Operation"]["S"]
                    if operation == "CREATE":
                        operation = "NEW"
                    resource_json = json.loads(new_image["Resource"]["S"])    
                    flat_json = convert_to_flat_json(resource_json, operation)
                    response = delta_table.put_item(
                        Item={
                            "PK": str(uuid.uuid4()),
                            "ImmsID": imms_id,
                            "Operation": operation,
                            "VaccineType": vaccine_type,
                            "SupplierSystem": "Pinnacle",
                            "DateTimeStamp": approximate_creation_time.isoformat(),
                            "Source": delta_source,
                            "Imms": flat_json,
                            "ExpiresAt": expiry_time_epoch,
                        }
                    )
                else:
                    operation_outcome["status"] = "200"
                    operation_outcome["status_code"] = "Record from DPS skipped"
                    log_data["operation_outcome"] = operation_outcome
                    firehose_log["event"] = log_data
                    firehose_logger.send_log(firehose_log)
                    return {"statusCode": 200, "body": "Record from DPS skipped"}
            else:
                operation = "REMOVE"
                new_image = record["dynamodb"]["Keys"]
                print(f"Record to delta:{new_image}")
                imms_id = new_image["PK"]["S"].split("#")[1]
                response = delta_table.put_item(
                    Item={
                        "PK": str(uuid.uuid4()),
                        "ImmsID": imms_id,
                        "Operation": "REMOVE",
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
                log = f"Record Successfully created for {imms_id}"
                operation_outcome["status"] = "200"
                operation_outcome["status_code"] = "Successfully synched into delta"
                log_data["operation_outcome"] = operation_outcome
                firehose_log["event"] = log_data
                firehose_logger.send_log(firehose_log)
            else:
                log = f"Record NOT created for {imms_id}"
                operation_outcome["status"] = "500"
                operation_outcome["status_code"] = "Exception"
                log_data["operation_outcome"] = operation_outcome
                firehose_log["event"] = log_data
                firehose_logger.send_log(firehose_log)
            logger.info(log)
        return {"statusCode": 200, "body": "Records processed successfully"}

    except Exception as e:
        operation_outcome["status"] = "500"
        operation_outcome["status_code"] = "Exception"
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
        raise Exception(f"Delta Lambda failure: {e}")
