import decimal
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, NotRequired, TypedDict

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from common.aws_dynamodb import get_dynamodb_table
from common.clients import STREAM_NAME, get_sqs_client, logger
from common.log_firehose import send_log_to_firehose
from converter import Converter
from mappings import ActionFlag, EventName, Operation

failure_queue_url = os.environ["AWS_SQS_QUEUE_URL"]
delta_table_name = os.environ["DELTA_TABLE_NAME"]
delta_source = os.environ["SOURCE"]
delta_ttl_days = os.environ["DELTA_TTL_DAYS"]
region_name = "eu-west-2"

delta_table = None


class ValidationError(Exception):
    pass


class OperationOutcomeDict(TypedDict):
    record: str
    operation_type: str
    statusCode: str
    statusDesc: str
    diagnostics: NotRequired[Any]


@dataclass(frozen=True)
class NormalizedRecord:
    event_id: str
    sequence_number: str
    operation: str
    primary_key: str
    imms_id: str
    patient_sort_key: str
    vaccine_type: str
    supplier_system: str
    creation_timestamp: float
    imms_raw: str | None  # raw Resource or Imms string, None for REMOVE


def _normalize_record(record: dict[str, Any]) -> NormalizedRecord:
    """
    Contract-first normalization of a raw DynamoDB stream record.
    All fallback chains are applied once here - fallbacks are used for order in tests. Processors consume NormalizedRecord only.

    Fallback chains (in order of precedence):
      sequence:      dynamodb.SequenceNumber -> NewImage.SequenceNumber -> "0"
      patient key:   NewImage.SK -> NewImage.PatientSK -> "default#unknown"
      operation:     NewImage.Operation -> mapped from eventName
      payload:       NewImage.Resource -> NewImage.Imms -> None
    """
    dynamodb = record.get("dynamodb", {})
    new_image = dynamodb.get("NewImage", {})
    keys = dynamodb.get("Keys", {})

    event_id = record.get("eventID", f"evt-{int(time.time() * 1000)}")

    # final fallback 0 ensures write is successful but losing sub-second ordering guatantee in edge cases where SequenceNumber is missing from stream record (should not happen in normal DynamoDB streams but added for robustness)
    sequence_number = (
        _extract_value(dynamodb.get("SequenceNumber")) or _extract_value(new_image.get("SequenceNumber")) or "0"
    )

    primary_key = _extract_value(new_image.get("PK")) or _extract_value(keys.get("PK")) or ""

    imms_id = (
        get_imms_id(primary_key)
        if isinstance(primary_key, str) and "#" in primary_key
        else str(_extract_value(new_image.get("ImmsID")) or "unknown")
    )

    patient_sort_key = (
        _extract_value(new_image.get("SK")) or _extract_value(new_image.get("PatientSK")) or "default#unknown"
    )

    vaccine_type = get_vaccine_type(str(patient_sort_key))

    operation = _extract_value(new_image.get("Operation")) or _event_to_operation(
        str(record.get("eventName", EventName.UPDATE))
    )

    supplier_system = _extract_value(new_image.get("SupplierSystem")) or "default"

    creation_timestamp = float(dynamodb.get("ApproximateCreationDateTime", time.time()))

    # Payload: Resource preferred, Imms fallback, None for REMOVE
    resource_raw = _extract_value(new_image.get("Resource"))
    imms_raw_field = _extract_value(new_image.get("Imms"))
    imms_raw: str | None
    if resource_raw is not None:
        imms_raw = resource_raw if isinstance(resource_raw, str) else json.dumps(resource_raw)
    elif imms_raw_field is not None:
        imms_raw = imms_raw_field if isinstance(imms_raw_field, str) else json.dumps(imms_raw_field)
    else:
        imms_raw = None

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
            delta_table = None
    return delta_table


def send_record_to_dlq(record: dict) -> None:
    try:
        get_sqs_client().send_message(QueueUrl=failure_queue_url, MessageBody=json.dumps(record))
        logger.info("Record saved successfully to the DLQ")
    except Exception:
        logger.exception("Error sending record to DLQ")


def get_vaccine_type(patient_sort_key: str) -> str:
    vaccine_type = patient_sort_key.split("#")[0]
    return str.strip(str.lower(vaccine_type))


def get_imms_id(primary_key: str) -> str:
    return primary_key.split("#")[1]


def _extract_value(raw: Any) -> Any:
    if isinstance(raw, dict) and len(raw) == 1:
        return next(iter(raw.values()))
    return raw


def get_creation_and_expiry_times(creation_timestamp: float, sequence_number: str) -> tuple[str, str, int]:
    """
    Generate timestamps and composite sort key for delta records.
    Args:
        creation_timestamp: Unix timestamp from DynamoDB stream (seconds precision)
        sequence_number: Sequence number from DynamoDB stream record for ordering guarantee
    Returns:
        Tuple of:
        - datetime_iso: ISO8601 datetime string (for backward compatibility)
        - datetime_with_sequence: Composite sort key with format "ISO8601#SEQUENCE" (for precise ordering)
        - expiry_timestamp: Unix timestamp for TTL (DELTA_TTL_DAYS)
    """
    creation_datetime = datetime.fromtimestamp(creation_timestamp, UTC)
    expiry_datetime = creation_datetime + timedelta(days=int(delta_ttl_days))
    expiry_timestamp = int(expiry_datetime.timestamp())
    datetime_iso = creation_datetime.isoformat()
    datetime_with_sequence = f"{datetime_iso}#{sequence_number}"
    return datetime_iso, datetime_with_sequence, expiry_timestamp


def handle_dynamodb_response(response, error_records):
    match response:
        case {"ResponseMetadata": {"HTTPStatusCode": 200}} if error_records:
            logger.warning(
                "Partial success: successfully synced into delta, "
                f"but issues found within record: {json.dumps(error_records)}"
            )
            return True, {
                "statusCode": "207",
                "statusDesc": "Partial success: successfully synced into delta, but issues found within record",
                "diagnostics": error_records,
            }
        case {"ResponseMetadata": {"HTTPStatusCode": 200}}:
            logger.info("Successfully synched into delta")
            return True, {
                "statusCode": "200",
                "statusDesc": "Successfully synched into delta",
            }
        case _:
            logger.error(f"Failure response from DynamoDB: {response}")
            return False, {
                "statusCode": "500",
                "statusDesc": "Failure response from DynamoDB",
                "diagnostics": response,
            }


def handle_exception_response(response):
    match response:
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
                "diagnostics": response,
            }


def _event_to_operation(event_name: str) -> str:
    if event_name == EventName.CREATE:
        return Operation.CREATE
    if event_name == EventName.UPDATE:
        return Operation.UPDATE
    if event_name == EventName.DELETE_PHYSICAL:
        return Operation.DELETE_PHYSICAL
    # DynamoDB stream REMOVE should map to physical delete
    if event_name == "REMOVE":
        return Operation.DELETE_PHYSICAL
    return Operation.UPDATE


def process_remove(record: dict[str, Any], table: Any | None = None) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)
    creation_datetime_str, datetime_with_sequence, expiry_timestamp = get_creation_and_expiry_times(
        norm.creation_timestamp, norm.sequence_number
    )
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
                "DateTimeStampWithSequence": datetime_with_sequence,
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


def process_skip(record: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)
    logger.info("Record from DPS skipped")
    return True, {
        "record": norm.imms_id,
        "operation_type": norm.operation,
        "statusCode": "200",
        "statusDesc": "Record from DPS skipped",
    }


def process_create_update_delete(record: dict[str, Any], table: Any | None = None) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)
    creation_datetime_str, datetime_with_sequence, expiry_timestamp = get_creation_and_expiry_times(
        norm.creation_timestamp, norm.sequence_number
    )
    operation_outcome: dict[str, Any] = {"record": norm.imms_id, "operation_type": norm.operation}

    error_records: list[dict[str, Any]] | None = None
    flat_json: Any

    if norm.operation == Operation.DELETE_PHYSICAL:
        flat_json = ""
        error_records = None
    else:
        action_flag = ActionFlag.CREATE if norm.operation == Operation.CREATE else norm.operation

        if norm.imms_raw is not None:
            resource_raw = _extract_value(record.get("dynamodb", {}).get("NewImage", {}).get("Resource"))
            if resource_raw is not None:
                resource_json = json.loads(norm.imms_raw, parse_float=decimal.Decimal)
                fhir_converter = Converter(resource_json, action_flag=action_flag)
                flat_json = fhir_converter.run_conversion()
                error_records = fhir_converter.get_error_records()
            else:
                flat_json = json.loads(norm.imms_raw, parse_float=decimal.Decimal)
                if isinstance(flat_json, dict) and "ACTION_FLAG" not in flat_json:
                    flat_json["ACTION_FLAG"] = action_flag
                error_records = None
        else:
            flat_json = {}
            if "ACTION_FLAG" not in flat_json:
                flat_json["ACTION_FLAG"] = action_flag
            error_records = None

    target_table = table or get_delta_table()
    if target_table is None:
        operation_outcome.update({"statusCode": "500", "statusDesc": "Delta table unavailable"})
        return False, operation_outcome

    try:
        response = target_table.put_item(
            Item={
                "PK": norm.event_id,
                "ImmsID": norm.imms_id,
                "Operation": norm.operation,
                "VaccineType": norm.vaccine_type,
                "SupplierSystem": norm.supplier_system,
                "DateTimeStamp": creation_datetime_str,
                "DateTimeStampWithSequence": datetime_with_sequence,
                "Source": delta_source,
                "Imms": flat_json,
                "ExpiresAt": expiry_timestamp,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        success, extra_log_fields = handle_dynamodb_response(response, error_records)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome
    except Exception as e:
        success, extra_log_fields = handle_exception_response(e)
        operation_outcome.update(extra_log_fields)
        return success, operation_outcome


def process_record(
    record: dict[str, Any],
    table: Any | None = None,
    sqs_client: Any | None = None,
    dlq_url: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Backward-compatible contract:
      - returns (success: bool, operation_outcome: dict)
      - optional dependency injection for tests
      - optional direct DLQ send when sqs_client + dlq_url are provided
    """
    try:
        event_name = str(record.get("eventName", ""))
        if event_name in (EventName.DELETE_PHYSICAL, "REMOVE"):
            success, outcome = process_remove(record, table=table)
        else:
            supplier_system = _extract_value(record.get("dynamodb", {}).get("NewImage", {}).get("SupplierSystem")) or ""
            if supplier_system in ("DPSFULL", "DPSREDUCED"):
                success, outcome = process_skip(record)
            else:
                success, outcome = process_create_update_delete(record, table=table)
    except Exception as exc:
        logger.exception("Exception during processing")
        success = False
        outcome = {
            "record": "unknown",
            "operation_type": _event_to_operation(str(record.get("eventName", EventName.UPDATE))),
            "statusCode": "500",
            "statusDesc": "Exception",
            "diagnostics": str(exc),
        }

    # Ensure stable schema keys
    if not isinstance(outcome, dict):
        outcome = {}

    if "record" not in outcome:
        outcome["record"] = "unknown"
    if "operation_type" not in outcome:
        outcome["operation_type"] = _event_to_operation(str(record.get("eventName", EventName.UPDATE)))
    if "statusCode" not in outcome:
        outcome["statusCode"] = "200" if success else "500"
    if "statusDesc" not in outcome:
        outcome["statusDesc"] = "Successfully synched into delta" if success else "Exception"

    # Optional direct DLQ path for tests/injected usage
    if not success and sqs_client is not None and dlq_url:
        try:
            sqs_client.send_message(QueueUrl=dlq_url, MessageBody=json.dumps(record, default=str))
        except Exception:
            logger.exception("Error sending record to DLQ")

    return success, outcome


def handler(event, _context) -> bool:
    logger.info("Starting Delta Handler")

    for record in event["Records"]:
        record_ingestion_datetime = datetime.now().isoformat()
        record_processing_start = time.time()
        success, operation_outcome = process_record(record)
        record_processing_end = time.time()
        log_data = {
            "function_name": "delta_sync",
            "operation_outcome": operation_outcome,
            "date_time": record_ingestion_datetime,
            "time_taken": f"{round(record_processing_end - record_processing_start, 5)}s",
        }
        send_log_to_firehose(STREAM_NAME, log_data)

        if not success:
            send_record_to_dlq(record)

    return True
