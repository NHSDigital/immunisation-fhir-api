import json
import time

import boto3
from botocore.exceptions import ClientError
from src.objectModels.mns_event.msn_event import MnsEvent

QUEUE_TEMPLATES = {
    "notification": "{env}-mns-test-notification-queue",
    "dead_letter": "{env}-mns-outbound-events-dead-letter-queue",
    "outbound": "{env}-mns-outbound-events-queue",
    "int_notification": "imms-int-publisher-subscribe-test",
    "int_dead_letter": "imms-int-publisher-subscribe-test-dlq",
}


def build_queue_url(env, aws_account_id, queue_type: str) -> str:
    if env == "preprod" and queue_type in ["notification", "dead_letter"]:
        queue_type = f"int_{queue_type}"

    if queue_type not in QUEUE_TEMPLATES:
        raise ValueError(f"Invalid queue_type: {queue_type}")

    queue_name = QUEUE_TEMPLATES[queue_type].format(env=env)

    return f"https://sqs.eu-west-2.amazonaws.com/{aws_account_id}/{queue_name}"


def read_message(
    context,
    queue_type="notification",
    wait_time_seconds=20,
    max_total_wait_seconds=120,
):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    expected_dataref = f"{context.url}/{context.ImmsID}"

    start_time = time.time()

    print(f"Waiting for message with dataref: {expected_dataref}")

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_total_wait_seconds:
            print("Stopping — reached max wait time.")
            return None

        print(f"Polling {queue_type} queue (wait {wait_time_seconds}s)...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            print("No messages returned — continuing to poll...")
            continue

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))
            dataref = body.dataref

            if dataref == expected_dataref:
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                print(f"Matched and deleted message for {dataref}")
                return body

            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
            print(f"Deleted non-matching message: {dataref}")


def purge_all_queues(env, aws_account_id):
    sqs = boto3.client("sqs", region_name="eu-west-2")

    if env == "preprod":
        queue_types = ["notification", "dead_letter"]  # will map to int_*
    else:
        queue_types = ["notification", "dead_letter", "outbound"]

    for queue_type in queue_types:
        queue_url = build_queue_url(env, aws_account_id, queue_type)

        print(f"Purging {queue_type} queue: {queue_url}")
        try:
            sqs.purge_queue(QueueUrl=queue_url)
            print(f"{queue_type.replace('_', ' ').title()} queue purged successfully\n")
        except ClientError as e:
            if e.response["Error"]["Code"] == "PurgeQueueInProgress":
                print(f"{queue_type.replace('_', ' ').title()} queue purge already in progress, skipping...\n")
            else:
                print(f"Error purging {queue_type} queue: {e}\n")


def read_messages_for_batch(
    context,
    queue_type="notification",
    valid_rows=None,
    wait_time_seconds=20,
    max_total_wait_seconds=180,
    expected_count=0,
):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    context.url = context.baseUrl + "/Immunization"

    expected_datarefs = {f"{context.url}/{str(row.IMMS_ID_CLEAN)}" for row in valid_rows}

    matched_messages = []
    start_time = time.time()

    print(f"Expecting {expected_count} messages for {len(valid_rows)} NHS numbers")

    while len(matched_messages) < expected_count:
        elapsed = time.time() - start_time
        if elapsed > max_total_wait_seconds:
            print("Stopping — reached max wait time.")
            break

        print(f"Polling SQS ({queue_type})...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            print("No messages returned — continuing to poll...")
            continue

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))
            dataref = body.dataref

            if dataref in expected_datarefs:
                matched_messages.append(body)
                print(f"Matched: {dataref}")

            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

    return matched_messages
