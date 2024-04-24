import boto3
import json
import os
from datetime import datetime, timedelta
import uuid
import logging
from botocore.exceptions import ClientError

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]


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


def handler(event, context):
    intrusion_check = True
    try:
        dynamodb = boto3.resource("dynamodb")
        delta_table = dynamodb.Table(delta_table_name)
        logging.basicConfig()
        logger = logging.getLogger()
        logger.setLevel("INFO")

        # Converting ApproximateCreationDateTime directly to string will give Unix timestamp
        # I am converting it to isofformat for filtering purpose. This can be changed accordingly

        for record in event["Records"]:
            intrusion_check = False
            approximate_creation_time = datetime.utcfromtimestamp(
                record["dynamodb"]["ApproximateCreationDateTime"]
            )
            expiry_time = approximate_creation_time + timedelta(days=30)
            expiry_time_epoch = int(expiry_time.timestamp())
            response = ""
            imms_id = ""
            if record["eventName"] != "REMOVE":
                new_image = record["dynamodb"]["NewImage"]
                imms_id = new_image["PK"]["S"].split("#")[1]
                response = delta_table.put_item(
                    Item={
                        "PK": str(uuid.uuid4()),
                        "ImmsID": imms_id,
                        "Operation": new_image["Operation"]["S"],
                        "DateTimeStamp": approximate_creation_time.isoformat(),
                        "Source": delta_source,
                        "Imms": new_image["Resource"]["S"],
                        "ExpiresAt": expiry_time_epoch,
                    }
                )
            else:
                new_image = record["dynamodb"]["Keys"]
                imms_id = new_image["PK"]["S"].split("#")[1]
                response = delta_table.put_item(
                    Item={
                        "PK": str(uuid.uuid4()),
                        "ImmsID": imms_id,
                        "Operation": "REMOVE",
                        "DateTimeStamp": approximate_creation_time.isoformat(),
                        "Source": delta_source,
                        "Imms": "",
                        "ExpiresAt": expiry_time_epoch,
                    }
                )

            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                log = f"Record Successfully created for {imms_id}"
            else:
                log = f"Record NOT created for {imms_id}"
            logger.info(log)
        return {
            "statusCode": 200,
            "body": json.dumps("Records processed successfully"),
        }

    except Exception as e:
        if intrusion_check:
            print("Incorrect invocation of Lambda")
        else:
            send_message(record)  # Send failed record details to DLQ
        raise Exception(f"Delta Lambda failure: {e}")
