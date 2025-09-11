import logging
import os
from typing import BinaryIO

import boto3
from smart_open import open

DESTINATION_BUCKET_NAME = os.getenv("DESTINATION_BUCKET_NAME")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3_client = boto3.client('s3')
sts_client = boto3.client('sts')

aws_account_id = sts_client.get_caller_identity()['Account']


def parse_headers(headers_str: str) -> dict[str, str]:
    headers = dict(
        header_str.split(":", 1)
        for header_str in headers_str.split("\r\n")
        if ":" in header_str
    )
    return {k.strip(): v.strip() for k, v in headers.items()}


def parse_header_value(header_value: str) -> tuple[str, dict[str, str]]:
    main_value, *params = header_value.split(";")
    parsed_params = dict(
        param.strip().split("=", 1)
        for param in params
    )
    parsed_params = {k: v.strip('"') for k, v in parsed_params.items()}
    return main_value, parsed_params


def read_until_part_start(input_file: BinaryIO, boundary: bytes) -> None:
    while line := input_file.readline():
        if line == b"--" + boundary + b"\r\n":
            return
    raise ValueError("Unexpected EOF")


def read_headers_bytes(input_file: BinaryIO) -> bytes:
    headers_bytes = b''
    while line := input_file.readline():
        if line == b"\r\n":
            return headers_bytes
        headers_bytes += line
    raise ValueError("Unexpected EOF")


def read_part_headers(input_file: BinaryIO) -> dict[str, str]:
    headers_bytes = read_headers_bytes(input_file)
    headers_str = headers_bytes.decode("utf-8")
    return parse_headers(headers_str)


def stream_part_body(input_file: BinaryIO, boundary: bytes, output_file: BinaryIO) -> None:
    previous_line = None
    found_part_end = False
    while line := input_file.readline():
        if line == b"--" + boundary + b"\r\n":
            logger.warning("Found additional part which will not be processed")
            found_part_end = True
        if line.startswith(b"--" + boundary + b"--"):
            found_part_end = True

        if previous_line is not None:
            if found_part_end:
                # The final \r\n is part of the encapsulation boundary, so should not be included
                output_file.write(previous_line.rstrip(b'\r\n'))
                return
            else:
                output_file.write(previous_line)

        previous_line = line
    raise ValueError("Unexpected EOF")


def move_file(source_bucket: str, source_key: str, destination_bucket: str, destination_key: str) -> None:
    s3_client.copy_object(
        CopySource={"Bucket": source_bucket, "Key": source_key},
        Bucket=destination_bucket,
        Key=destination_key,
        ExpectedBucketOwner=aws_account_id,
        ExpectedSourceBucketOwner=aws_account_id,
    )
    s3_client.delete_object(
        Bucket=source_bucket,
        Key=source_key,
        ExpectedBucketOwner=aws_account_id,
    )


def transfer_multipart_content(
    bucket_name: str,
    file_key: str,
    boundary: bytes,
    filename: str,
    checksum: str
) -> None:
    with open(
        f"s3://{bucket_name}/{file_key}",
        "rb",
        transport_params={"client": s3_client}
    ) as input_file:
        read_until_part_start(input_file, boundary)

        headers = read_part_headers(input_file)
        content_disposition = headers.get("Content-Disposition")
        if content_disposition:
            _, content_disposition_params = parse_header_value(content_disposition)
            filename = content_disposition_params.get("filename") or filename
        filename = add_checksum_to_filename(filename, checksum)
        content_type = headers.get("Content-Type") or "application/octet-stream"

        with open(
            f"s3://{DESTINATION_BUCKET_NAME}/streaming/{filename}",
            "wb",
            transport_params={
                "client": s3_client,
                "client_kwargs": {
                    "S3.Client.create_multipart_upload": {
                        "ContentType": content_type
                    }
                }
            }
        ) as output_file:
            stream_part_body(input_file, boundary, output_file)

        move_file(DESTINATION_BUCKET_NAME, f"streaming/{filename}", DESTINATION_BUCKET_NAME, filename)


def get_checksum_value(checksum_obj: dict[str, str]) -> str:
    return (
        checksum_obj.get("ChecksumCRC64NVME")
        or checksum_obj.get("ChecksumCRC32")
        or checksum_obj.get("ChecksumCRC32C")
        or checksum_obj.get("ChecksumSHA1")
        or checksum_obj.get("ChecksumSHA256")
        or checksum_obj.get("ChecksumMD5")
    )


def add_checksum_to_filename(filename: str, checksum: str) -> str:
    filename_parts = filename.rsplit(".", 1)
    return (
        f"{filename_parts[0]}_{checksum}.{filename_parts[1]}"
        if len(filename_parts) > 1
        else f"{filename}_{checksum}"
    )


def process_record(record: dict) -> None:
    bucket_name = record["s3"]["bucket"]["name"]
    file_key = record["s3"]["object"]["key"]
    logger.info(f"Processing {file_key}")

    head_object_response = s3_client.head_object(
        Bucket=bucket_name,
        Key=file_key,
        ExpectedBucketOwner=aws_account_id,
    )
    content_type = head_object_response['ContentType']
    media_type, content_type_params = parse_header_value(content_type)
    filename = head_object_response["Metadata"].get("mex-filename") or file_key

    get_object_attributes_response = s3_client.get_object_attributes(
        Bucket=bucket_name,
        Key=file_key,
        ObjectAttributes=["Checksum"],
        ExpectedBucketOwner=aws_account_id,
    )
    checksum_obj = get_object_attributes_response["Checksum"]
    checksum = get_checksum_value(checksum_obj)

    # Handle multipart content by parsing the filename from headers and streaming the content from the first part
    if media_type.startswith("multipart/"):
        logger.info("Found multipart content")
        boundary = content_type_params["boundary"].encode("utf-8")
        transfer_multipart_content(bucket_name, file_key, boundary, filename, checksum)
    else:
        s3_client.copy_object(
            Bucket=DESTINATION_BUCKET_NAME,
            CopySource={"Bucket": bucket_name, "Key": file_key},
            Key=add_checksum_to_filename(filename, checksum),
            ExpectedBucketOwner=aws_account_id,
            ExpectedSourceBucketOwner=aws_account_id,
        )

    logger.info(f"Transfer complete for {file_key}")

    move_file(bucket_name, file_key, bucket_name, f"archive/{file_key}")

    logger.info(f"Archived {file_key}")


def lambda_handler(event: dict, _context: dict) -> dict:
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
