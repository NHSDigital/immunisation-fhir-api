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

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
firehose_logger = FirehoseLogger()


def send_message(record):
    logger.info("Sending message to DLQ")
    # Create a message
    message_body = record
    # Use boto3 to interact with SQS
    sqs_client = boto3.client("sqs")
    try:
        # Send the record to the queue
        sqs_client.send_message(QueueUrl=failure_queue_url, MessageBody=json.dumps(message_body))
        logger.info("Record saved successfully to the DLQ")
    except ClientError as e:
        logger.error(f"Error sending record to DLQ: {e}")


def get_vaccine_type(patientsk) -> str:
    
    parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
    ret = parsed[0]
    logger.info(f"get_vaccine_type type: {ret}")
    return ret


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

        # Converting ApproximateCreationDateTime directly to string will give Unix timestamp
        # I am converting it to isofformat for filtering purpose. This can be changed accordingly

        n_records = len(event["Records"])
        logger.info(f"Number of records: {n_records}")
        record_n = 0
        for record in event["Records"]:
            logger.info(f"Process Record {record_n + 1} of {n_records}")
            firehose_log["event"] = record
            start = time.time()
            log_data["date_time"] = str(datetime.now())
            intrusion_check = False
            approximate_creation_time = datetime.utcfromtimestamp(record["dynamodb"]["ApproximateCreationDateTime"])
            expiry_time = approximate_creation_time + timedelta(days=30)
            expiry_time_epoch = int(expiry_time.timestamp())
            error_records = []
            response = str()
            imms_id = str()
            operation = str()

            logger.info(f"eventName: {record['eventName']}")

            # TODO Check correct event value for Deletion
            if not record["eventName"] in ["REMOVE", "DELETE"]:

                logger.info(f"Not a deletion event")

                new_image = record["dynamodb"]["NewImage"]
                imms_id = new_image["PK"]["S"].split("#")[1]
                logger.info(f"IMMS ID: {imms_id}")
                vaccine_type = get_vaccine_type(new_image["PatientSK"]["S"])
                supplier_system = new_image["SupplierSystem"]["S"]
                if supplier_system not in ("DPSFULL", "DPSREDUCED"):
                    logger.info("Not a DPSFULL or DPSREDUCED event")
                    operation = new_image["Operation"]["S"]
                    if operation == "CREATE":
                        operation = "NEW"
                    resource_json = json.loads(new_image["Resource"]["S"])
                    FHIRConverter = Converter(json.dumps(resource_json))
                    flat_json = FHIRConverter.runConversion(resource_json)  # Get the flat JSON
                    error_records = FHIRConverter.getErrorRecords()
                    flat_json["ACTION_FLAG"] = operation
                    logger.info("put item to delta")
                    # log imms 
                    imms = json.dumps(flat_json)
                    logger.info(f"IMMS: {imms}")
                    logger.info(f"Put record in delta. Operation: {operation}")  
                    response = delta_table.put_item(
                        Item={
                            "PK": str(uuid.uuid4()),
                            "ImmsID": imms_id,
                            "Operation": operation,
                            "VaccineType": vaccine_type,
                            "SupplierSystem": supplier_system,
                            "DateTimeStamp": approximate_creation_time.isoformat(),
                            "Source": delta_source,
                            "Imms": json.dumps(flat_json),
                            "ExpiresAt": expiry_time_epoch,
                        }
                    )
                else:
                    logger.info("DPSFULL or DPSREDUCED event")
                    operation_outcome["statusCode"] = "200"
                    operation_outcome["statusDesc"] = "Record from DPS skipped"
                    log_data["operation_outcome"] = operation_outcome
                    firehose_log["event"] = log_data
                    firehose_logger.send_log(firehose_log)
                    logger.info(f"Record from DPS skipped for {imms_id}")
                    logger.info("returning 200")
                    return {"statusCode": 200, "body": f"Record from DPS skipped for {imms_id}"}
            else:
                logger.info(f"Deletion event")
                operation = "REMOVE"
                new_image = record["dynamodb"]["Keys"]
                logger.info(f"Record to delta:{new_image}")
                imms_id = new_image["PK"]["S"].split("#")[1]
                logger.info(f"IMMS ID: {imms_id}")
                logger.info(f"Put record in delta. Operation: {operation}")  
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
                log_data["operation_outcome"] = operation_outcome
                firehose_log["event"] = log_data
                firehose_logger.send_log(firehose_log)
                logger.info(log)
                logger.info("Return 200")
                return {"statusCode": 200, "body": "Records processed successfully"}
            else:
                log = f"Record NOT created for {imms_id}"
                operation_outcome["statusCode"] = "500"
                operation_outcome["statusDesc"] = "Exception"
                log_data["operation_outcome"] = operation_outcome
                firehose_log["event"] = log_data
                firehose_logger.send_log(firehose_log)
                logger.info(log)
                logger.info("Return 500")
                return {"statusCode": 500, "body": "Records not processed successfully"}

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
        logger.info("Return 500 - Records not processed")
        return {
            "statusCode": 500,
            "body": "Records not processed",
        }
