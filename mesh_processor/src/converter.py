import logging
import os
from typing import BinaryIO

import boto3
from smart_open import open

DESTINATION_BUCKET_NAME = os.getenv("DESTINATION_BUCKET_NAME")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3_client = boto3.client('s3')


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
        Key=destination_key
    )
    s3_client.delete_object(Bucket=source_bucket, Key=source_key)


def transfer_multipart_content(bucket_name: str, file_key: str, boundary: bytes, filename: str) -> None:
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

        with open(
            f"s3://{DESTINATION_BUCKET_NAME}/streaming/{filename}",
            "wb",
            transport_params={"client": s3_client}
        ) as output_file:
            stream_part_body(input_file, boundary, output_file)

        move_file(DESTINATION_BUCKET_NAME, f"streaming/{filename}", DESTINATION_BUCKET_NAME, filename)


def process_record(record: dict) -> None:
    bucket_name = record["s3"]["bucket"]["name"]
    file_key = record["s3"]["object"]["key"]
    logger.info(f"Processing {file_key}")

    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    content_type = response['ContentType']
    media_type, content_type_params = parse_header_value(content_type)
    filename = response["Metadata"].get("mex-filename") or file_key

    # Handle multipart content by parsing the filename from headers and streaming the content from the first part
    if media_type.startswith("multipart/"):
        logger.info("Found multipart content")
        boundary = content_type_params["boundary"].encode("utf-8")
        transfer_multipart_content(bucket_name, file_key, boundary, filename)
    else:
        s3_client.copy_object(
            Bucket=DESTINATION_BUCKET_NAME,
            CopySource={"Bucket": bucket_name, "Key": file_key},
            Key=filename
        )

    logger.info(f"Transfer complete for {file_key}")


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
