import boto3
import os


def lambda_handler(event, context):
    s3 = boto3.client("s3")

    #  Destination bucket name
    destination_bucket = os.getenv("Destination_BUCKET_NAME")

    for record in event["Records"]:
        bucket_name = record["s3"]["bucket"]["name"]
        file_key = record["s3"]["object"]["key"]
        copy_source = {
            "Bucket": record["s3"]["bucket"]["name"],
            "Key": record["s3"]["object"]["key"],
        }

    # Read the .dat file from S3
    dat_obj = s3.get_object(Bucket=bucket_name, Key=file_key)

    # Update the filename from Metadata
    file_name = ensure_dat_extension(dat_obj["Metadata"].get("mex-filename", None))

    s3.copy_object(CopySource=copy_source, Bucket=destination_bucket, Key=file_name)

    return {"statusCode": 200, "body": "Files converted and uploaded successfully!"}


def ensure_dat_extension(file_name):
    if "." in file_name:
        # Split the filename and extension
        base_name, extension = file_name.rsplit(".", 1)

        # Check if the extension is not 'dat'
        if extension != "dat":
            file_name = f"{base_name}.dat"
    else:
        file_name += ".dat"

    return file_name
