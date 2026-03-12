import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_private_key_b64() -> str:
    # Generate a real RSA private key (PKCS8) and base64 encode the PEM
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(pem_bytes).decode("utf-8")


def load_sample_sqs_event() -> dict:
    """
    Loads the sample SQS event and normalises body to a JSON string (as SQS delivers it).
    Expects: lambdas/mns_publisher/tests/sqs_event.json
    """
    sample_event_path = Path(__file__).parent / "sample_data" / "sqs_event.json"
    with open(sample_event_path) as f:
        raw_event = json.load(f)

    if isinstance(raw_event.get("body"), dict):
        raw_event["body"] = json.dumps(raw_event["body"])

    return raw_event
