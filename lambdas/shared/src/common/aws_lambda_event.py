from typing import Dict, Any
from enum import Enum
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord
from common.clients import logger


class AwsEventType(Enum):
    SQS = "aws:sqs"
    S3 = "aws:s3"
    SNS = "aws:sns"
    UNKNOWN = "unknown"


class AwsLambdaEvent:

    def __init__(self):
        self.event_source = None
        self.records = []
        self.event_type = AwsEventType.UNKNOWN

    def load_event(self, event: Dict[str, Any]) -> None:
        self.event_source = event.get('eventSource')
        if self.event_source in [e.value for e in AwsEventType]:
            self.event_type = AwsEventType(self.event_source)
        else:
            self.event_type = AwsEventType.UNKNOWN

        if "Records" in event:
            records_dict = event.get('Records', [])
            if self.event_type == AwsEventType.SQS:
                self.records = [AwsLambdaSqsEventRecord(record) for record in records_dict]
            else:
                # not handled retain as Dict
                self.records = records_dict
        else:
            self.records = []
            logger.info("No records found in event")
