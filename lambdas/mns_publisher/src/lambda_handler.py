from aws_lambda_typing import context, events


def lambda_handler(event: events.SQSEvent, _: context.Context) -> bool:
    event_records = event.get("Records", [])

    for record in event_records:
        print(record)

    return True
