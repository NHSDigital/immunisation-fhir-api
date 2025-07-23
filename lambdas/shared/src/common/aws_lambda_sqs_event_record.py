from typing import Dict, Any


class AwsLambdaSqsEventRecord:
    def __init__(self, record: Dict[str, Any]):
        """Initialize from AWS SQS event dictionary"""
        self.message_id = record.get('messageId')
        self.receipt_handle = record.get('receiptHandle')
        self.body = record.get('body')
        self.attributes = record.get('attributes', {})
        self.message_attributes = record.get('messageAttributes', {})
        self.md5_of_body = record.get('md5OfBody')
        self.event_source = record.get('eventSource')
        self.event_source_arn = record.get('eventSourceARN')
        self.aws_region = record.get('awsRegion')
