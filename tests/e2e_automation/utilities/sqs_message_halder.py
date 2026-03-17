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


def read_message(
    context,
    queue_type="notification",
    action="CREATE",
    wait_for_message=True,
    max_empty_polls=3,
):
    sqs = boto3.client("sqs", region_name="eu-west-2")
    queue_url = build_queue_url(context.S3_env, context.aws_account_id, queue_type)

    expected_dataref = f"{context.url}/{context.ImmsID}"

    WAIT_TIME_SECONDS = 10
    empty_polls = 0

    while True:
        print(f"Polling {queue_type} queue (wait {WAIT_TIME_SECONDS}s)...")

        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=WAIT_TIME_SECONDS,
            VisibilityTimeout=30,
        )

        messages = response.get("Messages", [])

        if not messages:
            empty_polls += 1
            print(f"No messages returned (empty poll {empty_polls}/{max_empty_polls})")

            if not wait_for_message or empty_polls >= max_empty_polls:
                print("Stopping — queue quiet or wait disabled.")
                return None

            continue

        empty_polls = 0

        for msg in messages:
            body = MnsEvent(**json.loads(msg["Body"]))

            if body.dataref == expected_dataref and body.filtering.action == action:
                print(f"Matched message in {queue_type} queue: {body}")
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                print(f"Deleted message from {queue_type} queue")
                return body

            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
            print(f"Deleted non-matching message from {queue_type} queue")


def purge_all_queues(env, aws_account_id):
    sqs = boto3.client("sqs", region_name="eu-west-2")

    for queue_type in QUEUE_TEMPLATES.keys():
        queue_url = build_queue_url(env, aws_account_id, queue_type)

        print(f"Purging {queue_type} queue: {queue_url}")
        sqs.purge_queue(QueueUrl=queue_url)
        print(f"{queue_type.replace('_', ' ').title()} queue purged successfully\n")
