import json

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
    max_empty_polls=4,
    wait_time_seconds=20,
):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    expected_dataref = f"{context.url}/{context.ImmsID}"

    empty_polls = 0

    while True:
        print(f"Polling {queue_type} queue for messages (wait {wait_time_seconds}s)...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            empty_polls += 1
            print(f"No messages returned (empty poll {empty_polls}/{max_empty_polls})")

            if empty_polls >= max_empty_polls:
                print("Stopping — queue quiet or wait disabled.")
                return None

            continue

        empty_polls = 0

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))

            if body.dataref == expected_dataref:
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                print(f"Deleted matched message from {queue_type} queue")
                return body

            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
            print(f"Deleted non-matching message from {queue_type} queue")


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
    max_empty_polls=3,
    wait_time_seconds=20,
):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    context.url = context.baseUrl + "/Immunization"

    # Build expected datarefs from IMMS_ID_CLEAN
    expected_datarefs = {f"{context.url}/{str(row.IMMS_ID_CLEAN)}" for row in valid_rows}

    matched_messages = []
    empty_polls = 0

    print(f"Expecting {len(expected_datarefs)} MNS messages for this batch")

    while len(matched_messages) < len(expected_datarefs):
        print(f"Polling {queue_type} queue for messages (wait {wait_time_seconds}s)...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            empty_polls += 1
            print(f"No messages returned (empty poll {empty_polls}/{max_empty_polls})")

            if empty_polls >= max_empty_polls:
                print("Stopping — queue quiet, max empty polls reached.")
                break

            continue

        empty_polls = 0

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))
            dataref = body.dataref

            if dataref in expected_datarefs:
                matched_messages.append(body)
                print(f"Matched message for {dataref}")

            # Always delete — keep queue clean
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

    return matched_messages
