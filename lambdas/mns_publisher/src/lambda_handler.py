from aws_lambda_typing import context, events

from process_records import process_records


def lambda_handler(event: events.SQSEvent, _: context.Context) -> dict[str, list]:
    event_records = event.get("Records", [])

    return process_records(event_records)
