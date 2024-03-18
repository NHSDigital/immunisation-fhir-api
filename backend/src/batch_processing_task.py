import boto3
import os


def batch_processing(s3_client, source_bucket: str, destination_bucket: str, key: str):
    resp = s3_client.get_object(Bucket=source_bucket, Key=key)
    print(resp)
    content = resp["Body"].read().decode("utf-8")
    report = f"content: {content} | errors: []"
    resp = s3_client.put_object(Bucket=destination_bucket, Key=key, Body=report)
    print(resp)


if __name__ == '__main__':
    print(f"source-bucket: {os.getenv('SOURCE_BUCKET_NAME')} "
          f"destination-bucket: {os.getenv('DESTINATION_BUCKET_NAME')} key: {os.getenv('OBJECT_KEY')}")
    _client = boto3.client("s3")
    batch_processing(s3_client=_client, source_bucket=os.getenv('SOURCE_BUCKET_NAME'),
                     destination_bucket=os.getenv('DESTINATION_BUCKET_NAME'), key=os.getenv('OBJECT_KEY'))
