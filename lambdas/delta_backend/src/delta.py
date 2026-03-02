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
    operation: str | None  #  None for REMOVE events
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
    Processors consume NormalizedRecord only.

    Fields:
      sequence_number: dynamodb.SequenceNumber
      patient_sort_key: NewImage.PatientSK
      operation:        NewImage.Operation
      payload:          NewImage.Resource preferred, NewImage.Imms fallback, None for REMOVE
    """
    logger.info(
        "_normalize_record INPUT: eventName=%s dynamodb_keys=%s new_image_keys=%s",
        record.get("eventName"),
        list(record.get("dynamodb", {}).get("Keys", {}).keys()),
        list(record.get("dynamodb", {}).get("NewImage", {}).keys()),
    )

    dynamodb = record.get("dynamodb", {})
    new_image = dynamodb.get("NewImage", {})
    keys = dynamodb.get("Keys", {})

    event_id = record.get("eventID", f"evt-{int(time.time() * 1000)}")
    sequence_number: str = str(_extract_value(dynamodb.get("SequenceNumber")))
    primary_key = _extract_value(new_image.get("PK")) or _extract_value(keys.get("PK"))
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


def get_creation_and_expiry_times(creation_timestamp: float) -> tuple[str, int]:
    """
    Generate timestamps for delta records.
    Args:
        creation_timestamp: Unix timestamp from DynamoDB stream (seconds precision).
    Returns:
        Tuple of:
        - datetime_iso: ISO8601 datetime string (range key for SearchIndex GSI).
        - expiry_timestamp: Unix timestamp for TTL (DELTA_TTL_DAYS days from creation).
    """
    creation_datetime = datetime.fromtimestamp(creation_timestamp, UTC)
    expiry_datetime = creation_datetime + timedelta(days=int(delta_ttl_days))
    expiry_timestamp = int(expiry_datetime.timestamp())
    datetime_iso = creation_datetime.isoformat()
    logger.info(
        "Calculated creation and expiry times: datetime_iso=%s expiry_timestamp=%s creation_timestamp=%s",
        datetime_iso,
        expiry_timestamp,
        creation_datetime,
    )
    return datetime_iso, expiry_timestamp


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
    if event_name == EventName.DELETE_PHYSICAL:
        return Operation.DELETE_PHYSICAL
    if event_name == "REMOVE":
        return Operation.DELETE_PHYSICAL
    return Operation.UPDATE


def process_remove(record: dict[str, Any], table: Any | None = None) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)
    logger.info(
        "Processing REMOVE event norm record event_id=%s operation=%s imms_id=%s vaccine_type=%s supplier_system=%s",
        norm.event_id,
        norm.operation,
        norm.imms_id,
        norm.vaccine_type,
        norm.supplier_system,
    )
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


def process_skip(record: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)
    logger.info("Record from DPS skipped")
    logger.info(
        "DPS record details: event_id=%s operation=%s imms_id=%s vaccine_type=%s supplier_system=%s",
        norm.event_id,
        norm.operation,
        norm.imms_id,
        norm.vaccine_type,
        norm.supplier_system,
    )
    # norm.operation may be None for a skipped DPS record — log "UNKNOWN" rather than raising, since skipped records are not written to the delta table.
    return True, {
        "record": norm.imms_id,
        "operation_type": norm.operation or "UNKNOWN",
        "statusCode": "200",
        "statusDesc": "Record from DPS skipped",
    }


def process_create_update_delete(record: dict[str, Any], table: Any | None = None) -> tuple[bool, dict[str, Any]]:
    norm = _normalize_record(record)

    if norm.operation is None:
        raise ValidationError(
            f"Operation field missing from NewImage for event_id={norm.event_id}. "
            "Record cannot be safely classified — routing to DLQ."
        )

    logger.info(
        "Processing event event_id=%s operation=%s imms_id=%s vaccine_type=%s supplier_system=%s",
        norm.event_id,
        norm.operation,
        norm.imms_id,
        norm.vaccine_type,
        norm.supplier_system,
    )
    creation_datetime_str, expiry_timestamp = get_creation_and_expiry_times(norm.creation_timestamp)
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
                "SequenceNumber": norm.sequence_number,
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


def _route_record(
    record: dict[str, Any],
    table: Any | None,
) -> tuple[bool, dict[str, Any]]:
    """
    Decide which processor handles this record and call it.

    Raises:
        ValidationError: propagated from process_create_update_delete when Operation is absent.
        Exception: propagated to process_record's except block.
    """
    logger.info(
        "_route_record INPUT: eventName=%s supplierSystem=%s",
        record.get("eventName"),
        _extract_value(record.get("dynamodb", {}).get("NewImage", {}).get("SupplierSystem")),
    )
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
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Guarantee the operation outcome dict always has the four required keys.
    """
    if not isinstance(outcome, dict):
        outcome = {}

    outcome.setdefault("record", "unknown")
    outcome.setdefault(
        "operation_type",
        _event_to_operation(str(record.get("eventName", EventName.UPDATE))),
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
    sqs_client: Any | None = None,
    dlq_url: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Orchestrate processing of a single DDB stream record.
    """
    logger.info("Processing record with eventID=%s", record.get("eventID"))
    try:
        success, outcome = _route_record(record, table)
        logger.info("Record processing outcome: success=%s outcome=%s", success, outcome)
    except Exception as exc:
        logger.exception("Exception during processing")
        success = False
        outcome = {
            "record": "unknown",
            # _event_to_operation used here for error-path logging
            "operation_type": _event_to_operation(str(record.get("eventName", EventName.UPDATE))),
            "statusCode": "500",
            "statusDesc": "Exception",
            "diagnostics": str(exc),
        }

    outcome = _stable_outcome(outcome, success, record)
    logger.info("Final operation outcome after stable outcome: %s", outcome)
    _send_to_dlq_if_failed(success, record, sqs_client, dlq_url)
    return success, outcome


def handler(event, _context) -> bool:
    logger.info("Starting Delta Handler")
    logger.info("RAW_EVENT: %s", json.dumps(event, default=str))  # full stream batch
    logger.info("RECORD_COUNT: %d", len(event.get("Records", [])))

    # for record in event["Records"]:
    for i, record in enumerate(event["Records"]):
        logger.info(
            "RECORD[%d] eventName=%s eventID=%s sequenceNumber=%s",
            i,
            record.get("eventName"),
            record.get("eventID"),
            record.get("dynamodb", {}).get("SequenceNumber"),
        )

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
