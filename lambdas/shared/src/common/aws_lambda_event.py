from typing import Dict, Any
from enum import Enum
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord


class AwsEventType(Enum):
    SQS = "aws:sqs"
    S3 = "aws:s3"
    SNS = "aws:sns"
    UNKNOWN = "unknown"


class AwsLambdaEvent:

    def __init__(self, event: Dict[str, Any]):
        self.event_source = None
        self.event_type = AwsEventType.UNKNOWN
        self.event_source = event.get('eventSource')
        if self.event_source in [e.value for e in AwsEventType]:
            self.event_type = AwsEventType(self.event_source)

        self.records = []
        if "Records" in event:
            records_dict = event.get('Records', [])
            if self.event_type == AwsEventType.SQS:
                self.records = [AwsLambdaSqsEventRecord(record) for record in records_dict]
            else:
                self.records = records_dict
