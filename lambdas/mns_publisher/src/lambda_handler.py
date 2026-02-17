from aws_lambda_typing import context, events

from create_notification import create_mns_notification


def lambda_handler(event: events.SQSEvent, _: context.Context) -> bool:
    event_records = event.get("Records", [])

    for record in event_records:
        print(record)
        return create_mns_notification(record)

    return True
