import json
from pathlib import Path


def load_sample_sqs_event() -> dict:
    """
    Loads the sample SQS event and normalises body to a JSON string (as SQS delivers it).
    Expects: lambdas/mns_publisher/tests/sqs_event.json
    """
    sample_event_path = Path(__file__).parent / "sqs_event.json"
    with open(sample_event_path, "r") as f:
        raw_event = json.load(f)

    if isinstance(raw_event.get("body"), dict):
        raw_event["body"] = json.dumps(raw_event["body"])

    return raw_event
