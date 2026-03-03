import decimal
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import DynamoDBStreamEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from common.aws_dynamodb import get_dynamodb_table
from common.clients import STREAM_NAME, get_sqs_client
from common.log_firehose import send_log_to_firehose
from converter import Converter
from mappings import ActionFlag, EventName, Operation
from observability import logger
from types_delta import OperationOutcomeDict

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
delta_ttl_days = os.environ["DELTA_TTL_DAYS"]

delta_table = None


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class NormalizedRecord:
    event_id: str
    sequence_number: str
    operation: str | None  #  None for REMOVE events
    primary_key: str | None
    imms_id: str
    patient_sort_key: str | None
    vaccine_type: str
    supplier_system: str | None
    creation_timestamp: float
    imms_raw: str | None  # raw Resource or Imms string, None for REMOVE
    is_fhir_resource: bool  # True when imms_raw comes from Resource field


def get_vaccine_type(patient_sort_key: str) -> str:
    if not patient_sort_key:
        return "unknown"
    vaccine_type = patient_sort_key.split("#")[0]
    return str.strip(str.lower(vaccine_type))


def get_imms_id(primary_key: str) -> str:
    if not primary_key or "#" not in primary_key:
        return "unknown"
    return primary_key.split("#")[1]


def _extract_value(raw: Any) -> Any:
    if isinstance(raw, dict) and len(raw) == 1:
        return next(iter(raw.values()))
    return raw


def _event_to_operation(event_name: str) -> str:
    if event_name == EventName.CREATE:  # "INSERT"
        return Operation.CREATE
    if event_name == EventName.DELETE_PHYSICAL:  # "REMOVE"
        return Operation.DELETE_PHYSICAL
    return Operation.UPDATE  # "MODIFY", defult to UPDATE


# TODO: Accept DynamoDBRecord (aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event)
def _normalize_record(record: dict[str, Any]) -> NormalizedRecord:
    """
    Contract-first normalization of a raw DynamoDB stream record.
    Processors consume NormalizedRecord only.

    Fields:
      sequence_number: dynamodb.SequenceNumber
      patient_sort_key: NewImage.PatientSK
      operation:        NewImage.Operation
      payload:          NewImage.Resource preferred, NewImage.Imms fallback, None for REMOVE
    """
    dynamodb = record.get("dynamodb", {})
    new_image = dynamodb.get("NewImage", {})

    event_id = record.get("eventID", f"evt-{int(time.time() * 1000)}")
    sequence_number: str = str(dynamodb.get("SequenceNumber", "0"))
    primary_key = _extract_value(new_image.get("PK"))
    imms_id = get_imms_id(primary_key)
    patient_sort_key = _extract_value(new_image.get("PatientSK"))
    vaccine_type = get_vaccine_type(patient_sort_key)

    operation: str | None = _extract_value(new_image.get("Operation")) or None
    supplier_system = _extract_value(new_image.get("SupplierSystem"))
    creation_timestamp = float(dynamodb.get("ApproximateCreationDateTime", time.time()))

    # For REMOVE events NewImage is absent — both will be None.
    resource_raw: str | None = _extract_value(new_image.get("Resource"))
    imms_raw_field: str | None = _extract_value(new_image.get("Imms"))
    imms_raw: str | None = resource_raw if resource_raw is not None else imms_raw_field
    is_fhir_resource: bool = resource_raw is not None

    return NormalizedRecord(
        event_id=event_id,
        sequence_number=sequence_number,
        operation=operation,
        primary_key=primary_key,
        imms_id=imms_id,
        patient_sort_key=patient_sort_key,
        vaccine_type=vaccine_type,
        supplier_system=supplier_system,
        creation_timestamp=creation_timestamp,
        imms_raw=imms_raw,
        is_fhir_resource=is_fhir_resource,
    )


def get_delta_table():
    """
    Initialize the DynamoDB table resource with exception handling.
    """
    global delta_table
    if not delta_table:
        try:
            logger.info("Initializing Delta Table")
            delta_table = get_dynamodb_table(delta_table_name)
        except Exception as e:
            logger.error(f"Error initializing Delta Table: {e}")
            raise
    return delta_table


def get_creation_and_expiry_times(creation_timestamp: float) -> tuple[str, int]:
    """
    Generate timestamps for delta records.
    Args:
        creation_timestamp: Unix timestamp from DynamoDB stream (seconds precision).
    Returns:
        Tuple of:
        - datetime_iso: ISO8601 datetime string (range key for SearchIndex GSI).
        - expiry_timestamp: Unix timestamp for DELTA_TTL_DAYS from creation.
    """
    creation_datetime = datetime.fromtimestamp(creation_timestamp, UTC)
    expiry_datetime = creation_datetime + timedelta(days=int(delta_ttl_days))
    expiry_timestamp = int(expiry_datetime.timestamp())
    datetime_iso = creation_datetime.isoformat()
    return datetime_iso, expiry_timestamp


def handle_dynamodb_response(
    response: dict[str, Any], error_records: list[dict[str, Any]] | None
) -> tuple[bool, dict[str, Any]]:
    match response:
        case {"ResponseMetadata": {"HTTPStatusCode": 200}} if error_records:
            logger.warning(
                "Partial success: record synced with conversion errors",
                extra={"conversion_errors": error_records},
            )
            return True, {
                "statusCode": "207",
                "statusDesc": "Partial success: successfully synced into delta, but issues found within record",
                "diagnostics": error_records,
            }
        case {"ResponseMetadata": {"HTTPStatusCode": 200}}:
            return True, {
                "statusCode": "200",
                "statusDesc": "Successfully synched into delta",
            }
        case _:
            logger.error(
                "Failure response from DynamoDB",
                extra={"dynamodb_response": response},
            )
            return False, {
                "statusCode": "500",
                "statusDesc": "Failure response from DynamoDB",
                "diagnostics": response,
            }


def handle_exception_response(exc: Exception) -> tuple[bool, dict[str, Any]]:
    match exc:
        case ClientError(response={"Error": {"Code": "ConditionalCheckFailedException"}}):
            logger.info("Skipped record already present in delta")
            return True, {
                "statusCode": "200",
                "statusDesc": "Skipped record already present in delta",
            }
        case _:
            logger.exception("Exception during processing")
            return False, {
                "statusCode": "500",
                "statusDesc": "Exception",
                "diagnostics": str(exc),
            }


def process_remove(
    record: dict[str, Any],
    table: Any | None = None,
) -> tuple[bool, OperationOutcomeDict]:
    norm = _normalize_record(record)
    creation_datetime_str, expiry_timestamp = get_creation_and_expiry_times(norm.creation_timestamp)
    operation_outcome: dict[str, Any] = {"operation_type": Operation.DELETE_PHYSICAL, "record": norm.imms_id}

    target_table = table or get_delta_table()
    if target_table is None:
        operation_outcome.update({"statusCode": "500", "statusDesc": "Delta table unavailable"})
        return False, operation_outcome

    try:
        response = target_table.put_item(
            Item={
                "PK": norm.event_id,
                "ImmsID": norm.imms_id,
                "Operation": Operation.DELETE_PHYSICAL,
                "VaccineType": norm.vaccine_type,
                "SupplierSystem": norm.supplier_system,
                "DateTimeStamp": creation_datetime_str,
                "SequenceNumber": norm.sequence_number,
                "Source": delta_source,
                "Imms": "",
                "ExpiresAt": expiry_timestamp,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        success, extra_log_fields = handle_dynamodb_response(response, None)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome
    except Exception as e:
        success, extra_log_fields = handle_exception_response(e)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome


def process_skip(record: dict[str, Any]) -> tuple[bool, OperationOutcomeDict]:
    norm = _normalize_record(record)
    logger.info("Record from DPS skipped")
    # norm.operation may be None for a skipped DPS record — log "UNKNOWN" rather than raising, since skipped records are not written to the delta table.
    return True, {
        "record": norm.imms_id,
        "operation_type": norm.operation or "UNKNOWN",
        "statusCode": "200",
        "statusDesc": "Record from DPS skipped",
    }


def process_create_update_delete(
    record: dict[str, Any],
    table: Any | None = None,
) -> tuple[bool, OperationOutcomeDict]:
    norm = _normalize_record(record)

    if norm.operation is None:
        raise ValidationError(
            f"Operation field missing from NewImage for event_id={norm.event_id}. "
            "Record cannot be safely classified — routing to DLQ."
        )

    creation_datetime_str, expiry_timestamp = get_creation_and_expiry_times(norm.creation_timestamp)
    operation_outcome: dict[str, Any] = {
        "record": norm.imms_id,
        "operation_type": norm.operation,
    }

    action_flag = ActionFlag.CREATE if norm.operation == Operation.CREATE else norm.operation

    if norm.imms_raw is None:
        raise ValidationError(
            f"Imms/Resource payload missing from NewImage for event_id={norm.event_id}. "
            "Record cannot be processed — routing to DLQ."
        )

    if norm.is_fhir_resource:
        resource_json = json.loads(norm.imms_raw, parse_float=decimal.Decimal)
        fhir_converter = Converter(resource_json, action_flag=action_flag)
        flat_json = fhir_converter.run_conversion()
        error_records: list[dict[str, Any]] | None = fhir_converter.get_error_records()
    else:
        flat_json = json.loads(norm.imms_raw, parse_float=decimal.Decimal)
        if isinstance(flat_json, dict) and "ACTION_FLAG" not in flat_json:
            flat_json["ACTION_FLAG"] = action_flag
        error_records = None

    target_table = table or get_delta_table()
    if target_table is None:
        operation_outcome.update({"statusCode": "500", "statusDesc": "Delta table unavailable"})
        return False, operation_outcome  # type: ignore[return-value]

    try:
        response = target_table.put_item(
            Item={
                "PK": norm.event_id,
                "ImmsID": norm.imms_id,
                "Operation": norm.operation,
                "VaccineType": norm.vaccine_type,
                "SupplierSystem": norm.supplier_system,
                "DateTimeStamp": creation_datetime_str,
                "SequenceNumber": norm.sequence_number,
                "Source": delta_source,
                "Imms": flat_json,
                "ExpiresAt": expiry_timestamp,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        success, extra_fields = handle_dynamodb_response(response, error_records)
        operation_outcome.update(extra_fields)
        return success, operation_outcome
    except Exception as exc:
        success, extra_fields = handle_exception_response(exc)
        operation_outcome.update(extra_fields)
        return success, operation_outcome


def _route_record(
    record: dict[str, Any],
    table: Any | None,
) -> tuple[bool, OperationOutcomeDict]:
    """
    Route a stream record to the correct processor.

    Raises:
        ValidationError: from process_create_update_delete when Operation is absent.
        Exception: any unexpected processor exception — propagated to process_record.
    """
    event_name = str(record.get("eventName", ""))

    if event_name == EventName.DELETE_PHYSICAL:
        return process_remove(record, table=table)

    supplier_system = _extract_value(record.get("dynamodb", {}).get("NewImage", {}).get("SupplierSystem")) or ""
    if supplier_system in ("DPSFULL", "DPSREDUCED"):
        return process_skip(record)

    return process_create_update_delete(record, table=table)


def _stable_outcome(
    outcome: Any,
    success: bool,
    event_name: str,
) -> OperationOutcomeDict:
    """
    Guarantee the operation outcome dict always has the four required keys.
    """
    if not isinstance(outcome, dict):
        outcome = {}

    outcome.setdefault("record", "unknown")
    outcome.setdefault(
        "operation_type",
        _event_to_operation(str(event_name)),
    )
    outcome.setdefault("statusCode", "200" if success else "500")
    outcome.setdefault(
        "statusDesc",
        "Successfully synched into delta" if success else "Exception",
    )
    return outcome


def _send_to_dlq_if_failed(
    success: bool,
    record: dict[str, Any],
    sqs_client: Any | None,
    dlq_url: str | None,
) -> None:
    """
    Optionally send a failed record to the DLQ via an injected SQS client.
    No-op when success is True or when sqs_client / dlq_url are not provided.
    """
    if success or sqs_client is None or not dlq_url:
        return
    try:
        sqs_client.send_message(
            QueueUrl=dlq_url,
            MessageBody=json.dumps(record, default=str),
        )
    except Exception:
        logger.exception("Error sending record to DLQ")


def process_record(
    record: dict[str, Any],
    table: Any | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Orchestrate processing of a single DDB stream record.

    Args:
        record:     Raw DynamoDB stream record dict.
        table:      Injected DynamoDB Table resource (tests override).

    Returns:
        (success, operation_outcome) — outcome always has all four required keys.
    """
    event_name: str = str(record.get("eventName") or "")

    with logger.append_context_keys(
        event_id=record.get("eventID", "unknown"),
        event_name=event_name or "UNKNOWN",
    ):
        try:
            success, outcome = _route_record(record, table)
        except Exception as e:
            logger.exception("Unhandled exception during record processing")
            success = False
            outcome = {  # type: ignore[assignment]
                "record": "unknown",
                "operation_type": _event_to_operation(event_name),
                "statusCode": "500",
                "statusDesc": "Exception",
                "diagnostics": str(e),
            }

        outcome = _stable_outcome(outcome, success, event_name)
        return success, outcome


def handler(event: dict[str, Any], _context: LambdaContext) -> bool:
    if "Records" not in event:
        # preserves existing test/contract
        raise KeyError("Records")
    stream_event = DynamoDBStreamEvent(event)

    logger.info("Delta handler invoked", extra={"record_count": len(event["Records"])})

    table = get_delta_table()
    sqs = get_sqs_client()

    for typed_record in stream_event.records:
        # TODO: refactor process_record to accept DynamoDBRecord directly
        record = typed_record.raw_event
        record_ingestion_datetime = datetime.now(UTC).isoformat()
        record_processing_start = time.time()
        success, operation_outcome = process_record(
            record,
            table=table,
        )
        _send_to_dlq_if_failed(success, record, sqs, failure_queue_url)

        record_processing_end = time.time()
        log_data = {
            "function_name": "delta_sync",
            "operation_outcome": operation_outcome,
            "date_time": record_ingestion_datetime,
            "time_taken": f"{round(record_processing_end - record_processing_start, 5)}s",
        }
        send_log_to_firehose(STREAM_NAME, log_data)

    return True
