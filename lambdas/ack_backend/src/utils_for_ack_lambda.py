"""Utils for ack lambda"""
from audit_table import get_record_count_by_message_id

_BATCH_EVENT_ID_TO_RECORD_COUNT_MAP: dict[str, int] = {}


def is_ack_processing_complete(batch_event_message_id: str, processed_ack_count: int) -> bool:
    """Checks if we have received all the acknowledgement rows for the original source file. Also caches the value of
    the source file record count to reduce traffic to DynamoDB"""
    if batch_event_message_id in _BATCH_EVENT_ID_TO_RECORD_COUNT_MAP:
        return _BATCH_EVENT_ID_TO_RECORD_COUNT_MAP[batch_event_message_id] == processed_ack_count

    record_count = get_record_count_by_message_id(batch_event_message_id)

    if not record_count:
        # Record count is not set on the audit item until all rows have been preprocessed and sent to Kinesis
        return False

    _BATCH_EVENT_ID_TO_RECORD_COUNT_MAP[batch_event_message_id] = record_count
    return record_count == processed_ack_count
