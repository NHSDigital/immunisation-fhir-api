import logging

import boto3
import os


DESTINATION_BUCKET_NAME = os.getenv("DESTINATION_BUCKET_NAME")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3_client = boto3.client('s3')


def parse_headers(headers_str: str):
    headers = dict(
        header_str.split(":", 1)
        for header_str in headers_str.split("\r\n")
        if ":" in header_str
    )
    return {k.strip(): v.strip() for k, v in headers.items()}


def parse_header_value(header_value: str):
    main_value, *params = header_value.split(";")
    parsed_params = dict(
        param.strip().split("=", 1)
        for param in params
    )
    parsed_params = {k: v.strip('"') for k, v in parsed_params.items()}
    return main_value, parsed_params


def process_record(record):
    bucket_name = record["s3"]["bucket"]["name"]
    file_key = record["s3"]["object"]["key"]
    logger.info(f"Processing {file_key}")

    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    filename = response["Metadata"].get("mex-filename") or file_key
    # TODO - this will read everything into memory - look at streaming instead
    content = response["Body"].read().decode("utf-8")

    content_type = response['ContentType']
    media_type, content_type_params = parse_header_value(content_type)

    # Handle multipart content by parsing the filename and content from the first part
    if media_type.startswith("multipart/"):
        logger.info("Found multipart content")
        boundary = content_type_params["boundary"]
        parts = [
            part.lstrip(f"--{boundary}")
            for part in content.split(f"\r\n--{boundary}")
            if part.strip() != "" and part.strip() != "--"
        ]
        if len(parts) > 1:
            logger.warning(f"Got {len(parts)} parts, but will only process the first")

        headers_str, content = parts[0].split("\r\n\r\n", 1)
        headers = parse_headers(headers_str)
        content_disposition = headers["Content-Disposition"]
        _, content_disposition_params = parse_header_value(content_disposition)
        filename = content_disposition_params.get("filename") or filename

    s3_client.put_object(Bucket=DESTINATION_BUCKET_NAME, Key=filename, Body=content.encode("utf-8"))


def lambda_handler(event, _):
    success = True

    for record in event["Records"]:
        try:
            process_record(record)
        except Exception:
            logger.exception("Failed to process record")
            success = False

    return {
        'statusCode': 200,
        'body': 'Files converted and uploaded successfully!'
    } if success else {
        'statusCode': 500,
        'body': 'Errors occurred during processing'
    }
