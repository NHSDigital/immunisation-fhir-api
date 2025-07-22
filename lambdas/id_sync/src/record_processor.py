'''
    record Processor
'''
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord
from common.clients import logger


def process_record(event_record, _):
    record = AwsLambdaSqsEventRecord(event_record) if isinstance(event_record, dict) else event_record
    logger.info("Processing record: %s", record)
    return f"hello world {record}"
