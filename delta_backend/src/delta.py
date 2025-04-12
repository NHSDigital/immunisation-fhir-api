from log_firehose import FirehoseLogger
firehose_logger = FirehoseLogger()

def handler(event, context):
    firehose_logger.send_log(event)    
    return { "statusCode": 200  }
