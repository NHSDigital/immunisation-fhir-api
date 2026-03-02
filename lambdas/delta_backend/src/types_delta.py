"""
Typed contracts for the Delta Lambda.

All TypedDicts here are the single source of truth for:
  - DynamoDB stream record shapes
  - Normalized record fields
  - Operation outcome payloads
  - Firehose log payloads
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class DynamoDBAttributeValue(TypedDict, total=False):
    """Single DynamoDB marshalled attribute, e.g. {"S": "value"} or {"N": "1"}."""

    S: str
    N: str
    B: bytes
    BOOL: bool
    NULL: bool
    L: list[Any]
    M: dict[str, Any]


class DynamoDBNewImage(TypedDict, total=False):
    PK: DynamoDBAttributeValue
    PatientSK: DynamoDBAttributeValue
    Operation: DynamoDBAttributeValue
    SupplierSystem: DynamoDBAttributeValue
    Resource: DynamoDBAttributeValue
    Imms: DynamoDBAttributeValue
    SequenceNumber: DynamoDBAttributeValue
    Version: DynamoDBAttributeValue


class DynamoDBKeys(TypedDict, total=False):
    PK: DynamoDBAttributeValue
    PatientSK: DynamoDBAttributeValue
    SupplierSystem: DynamoDBAttributeValue


class DynamoDBEnvelope(TypedDict, total=False):
    ApproximateCreationDateTime: float
    SequenceNumber: str
    NewImage: DynamoDBNewImage
    Keys: DynamoDBKeys
    StreamViewType: str
    SizeBytes: int


class StreamRecord(TypedDict):
    """
    A single record from a DynamoDB Streams Lambda event.
    Shape documented in README.md § Delta Stream Input Contract.
    """

    eventID: str
    eventName: str
    dynamodb: DynamoDBEnvelope
    eventSource: NotRequired[str]
    awsRegion: NotRequired[str]


class StreamEvent(TypedDict):
    """Top-level Lambda event from DynamoDB Streams."""

    Records: list[StreamRecord]


class OperationOutcomeDict(TypedDict):
    """
    Guaranteed shape returned by process_record().
    All four keys are always present after _stable_outcome() runs.
    """

    record: str  # imms_id or "unknown"
    operation_type: str  # Operation.*
    statusCode: str  # "200" | "207" | "500"
    statusDesc: str
    diagnostics: NotRequired[Any]


class FirehoseLogPayload(TypedDict):
    """
    Payload sent to Splunk via send_log_to_firehose().
    Mirrors the shape asserted in test_partial_success_contract_and_dlq_routing.
    """

    function_name: str
    operation_outcome: OperationOutcomeDict
    date_time: str
    time_taken: str
