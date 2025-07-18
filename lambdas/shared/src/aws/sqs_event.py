from typing import List, Dict, Any
from sqs_event_record import SQSEventRecord


class SQSEvent:
    def __init__(self, records: List[SQSEventRecord]):
        self.records = records

    @classmethod
    def from_event(cls, event: Dict[str, Any]):
        records = [SQSEventRecord.from_dict(record) for record in event.get('Records', [])]
        return cls(records=records)

    def __repr__(self):
        return f"<SQSEvent records={len(self.records)}>"
