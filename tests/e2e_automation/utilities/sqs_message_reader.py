import json

import boto3
from src.objectModels.mns_event.msn_event import MnsEvent

QUEUE_TEMPLATES = {
    "notification": "{env}-mns-test-notification-queue",
    "dead_letter": "{env}-mns-outbound-events-dead-letter-queue",
    "outbound": "{env}-mns-outbound-events-queue",
}


def build_queue_url(env, aws_account_id, queue_type: str) -> str:
    if queue_type not in QUEUE_TEMPLATES:
        raise ValueError(f"Invalid queue_type: {queue_type}")

    queue_name = QUEUE_TEMPLATES[queue_type].format(env=env)

    return f"https://sqs.eu-west-2.amazonaws.com/{aws_account_id}/{queue_name}"


def read_message(context, queue_type="notification", wait_for_message=True):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    expected_dataref = f"{context.url}/{context.ImmsID}"

    MAX_ATTEMPTS = 5 if wait_for_message else 1
    WAIT_TIME_SECONDS = 10

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Attempt {attempt}/{MAX_ATTEMPTS} — waiting up to {WAIT_TIME_SECONDS}s...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=WAIT_TIME_SECONDS,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            print("No messages returned in this attempt.")
            continue

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))

            if body.dataref == expected_dataref:
                print(f"Matched message in {queue_type} queue: {body}")
                return body, msg["ReceiptHandle"]

    print("Message did not arrive after all attempts.")
    return None, None


def delete_message(context, receipt_handle: str, queue_type="notification"):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    print(f"Deleted message from {queue_type} queue")


def purge_all_queues(env, aws_account_id):
    sqs = boto3.client("sqs", region_name="eu-west-2")

    for queue_type in QUEUE_TEMPLATES.keys():
        queue_url = build_queue_url(env, aws_account_id, queue_type)

        print(f"Purging {queue_type} queue: {queue_url}")
        sqs.purge_queue(QueueUrl=queue_url)
        print(f"{queue_type.replace('_', ' ').title()} queue purged successfully\n")
