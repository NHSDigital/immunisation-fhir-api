import boto3
from botocore.exceptions import ClientError


def get_queue_url(queue_name):
    """
    Retrieves the URL of an SQS queue by its name.
    Args:
        queue_name: The name of the SQS queue.
    Returns:
        The URL of the SQS queue, or None if not found.
    """
    sqs_client = boto3.client("sqs")
    try:
        response = sqs_client.get_queue_url(QueueName=queue_name)
        return response["QueueUrl"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "QueueDoesNotExist":
            print(f"Queue with name {queue_name} does not exist.")
        else:
            print(f"Error getting queue URL: {e}")
        return None
