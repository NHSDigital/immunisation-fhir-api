import json
from update_ack_file import update_ack_file


def lambda_handler(event, context):

    try:
        imms_id = None
        successful_api_response = True
        print(f"event: {event}")
        for record in event["Records"]:
            body_json = record["body"]
            incoming_message_body = json.loads(body_json)
            # Check if there are any messages to process
            file_key = incoming_message_body.get("file_key")
            row_id = incoming_message_body.get("row_id")
            local_id = incoming_message_body.get("local_id")
            imms_id = incoming_message_body.get("imms_id")
            diagnostics = incoming_message_body.get("diagnostics")
            created_at_formatted_string = incoming_message_body.get(
                "created_at_formatted_string"
            )
            if diagnostics is None:
                successful_api_response = True
            else:
                successful_api_response = False

            update_ack_file(
                file_key,
                local_id,
                row_id,
                successful_api_response=successful_api_response,
                diagnostics=diagnostics,
                imms_id=imms_id,
                created_at_formatted_string=created_at_formatted_string,
            )


    except Exception as e:
        print(f"Error processing SQS message: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps("Lambda function executed successfully!"),
    }
