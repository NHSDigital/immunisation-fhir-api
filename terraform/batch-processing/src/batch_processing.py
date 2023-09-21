from time import time
from boto3 import resource


def lambda_handler(_event, _context):
    source_bucket_name = _event.get("Records")[0].get("s3").get("bucket").get("name")
    dest_bucket_name = source_bucket_name.replace("source", "destination")
    output_bucket = resource('s3').Bucket(dest_bucket_name)

    # Write some placeholder bytestring data to a file in the bucket,
    # so we can test that the lambda writes to the correct output bucket.
    filename = f"output_report_{time()}.txt"
    data = (b'Test file to see if the lambda writes to the correct s3 bucket. '
            b'If our AWS bill skyrockets, this file has been written to the wrong bucket!')

    output_bucket.put_object(Body=data, Key=filename)

    return {
        'statusCode': 200
    }
