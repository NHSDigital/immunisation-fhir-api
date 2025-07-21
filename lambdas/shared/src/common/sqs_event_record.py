from typing import Dict, Any


class SQSEventRecord:
    def __init__(self, message_id: str, receipt_handle: str, body: str, attributes: Dict[str, str],
                 message_attributes: Dict[str, Any], md5_of_body: str, event_source: str,
                 event_source_arn: str, aws_region: str):
        self.message_id = message_id
        self.receipt_handle = receipt_handle
        self.body = body
        self.attributes = attributes
        self.message_attributes = message_attributes
        self.md5_of_body = md5_of_body
        self.event_source = event_source
        self.event_source_arn = event_source_arn
        self.aws_region = aws_region

    @classmethod
    def from_dict(cls, record: Dict[str, Any]):
        return cls(
            message_id=record['messageId'],
            receipt_handle=record['receiptHandle'],
            body=record['body'],
            attributes=record.get('attributes', {}),
            message_attributes=record.get('messageAttributes', {}),
            md5_of_body=record['md5OfBody'],
            event_source=record['eventSource'],
            event_source_arn=record['eventSourceARN'],
            aws_region=record['awsRegion']
        )

    def __repr__(self):
        return f"<SQSEventRecord id={self.message_id}>"
