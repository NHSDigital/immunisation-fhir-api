import boto3
import json
import logging
from log_firehose import FirehoseLogger

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
firehose_logger = None

def handler(event, context):
    global  firehose_logger
    logger.info("Starting Delta Handler")
    logger.info(f"Event: {event["text"]}")
    
    if firehose_logger is None:
        firehose_logger = FirehoseLogger()
        logger.info("FirehoseLogger initialized")

    firehose_logger.send_log(event)