import boto3
from botocore.exceptions import ClientError


def read_and_delete_messages(queue_url):
    """
    Reads and deletes messages from an SQS queue.
    Args:
        queue_url: The URL of the SQS queue.
    """
    sqs_client = boto3.client("sqs")
    try:
        # Receive messages with a maximum of 10 messages per request
        response = sqs_client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        )

        # Check if there are any messages
        if "Messages" not in response:
            # print("No messages found in the queue.")
            return
        # Process and delete each message
        for message in response["Messages"]:
            # Access message body
            # message_body = message["Body"]
            # Process the message (replace with your actual processing logic)
            # print(f"Processing message: {message_body}")
            # Get the receipt handle for deletion
            receipt_handle = message["ReceiptHandle"]
            # Delete the message from the queue
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            # print(f"Deleted message: {message_body}")
    except ClientError as e:
        print(f"Error accessing SQS: {e}")
