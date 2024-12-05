import json
import logging
from typing import Union
from datetime import datetime
from log_structure_splunk import ack_function_info
from log_firehose_splunk import FirehoseLogger
from update_ack_file import update_ack_file, create_ack_data

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


firehose_logger = FirehoseLogger()


@ack_function_info
def lambda_handler(event, context):
    try:
        imms_id = None
        successful_api_response = True
        array_of_rows = []
        for record in event["Records"]:
            body_json = record["body"]
            incoming_message_body = json.loads(body_json)
            for item in incoming_message_body:
                # Check if there are any messages to process
                file_key = item.get("file_key")
                row_id = item.get("row_id")
                local_id = item.get("local_id")
                imms_id = item.get("imms_id")
                diagnostics = item.get("diagnostics")
                created_at_formatted_string = item.get("created_at_formatted_string")
                if diagnostics is None:
                    successful_api_response = True
                else:
                    successful_api_response = False
                row = create_ack_data(
                    created_at_formatted_string, local_id, row_id, successful_api_response, diagnostics, imms_id
                )
                array_of_rows.append(row)
                print(array_of_rows)
        update_ack_file(file_key, created_at_formatted_string=created_at_formatted_string, ack_data_rows=array_of_rows)
        # Delete the message from the queue

    except Exception as e:

        print(f"Error processing SQS message: {e}")
        log_data = {
            "status": "fail",
            "statusCode": 500,
            "diagnostics": f"Error processing SQS message: {str(e)}",
            "date_time": str(datetime.now()),
            "error_source": "ack_lambda_handler",
        }
        firehose_log = dict()
        firehose_log["event"] = log_data
        firehose_logger.ack_send_log(firehose_log)

    return {
        "statusCode": 200,
        "body": json.dumps("Lambda function executed successfully!"),
    }
