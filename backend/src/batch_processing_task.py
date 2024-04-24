import boto3
import logging
import os
import time
import uuid
from botocore.config import Config
from datetime import datetime

from authentication import AppRestrictedAuth, Service
from batch.immunization_api import ImmunizationApi
from batch.parser import DataParser
from batch.processor import BatchData, BatchProcessor
from batch.report import ReportGenerator, ReportEntryTransformer, S3FixedBufferStream
from batch.transformer import DataRecordTransformer
from cache import Cache


def _make_batch_data() -> BatchData:
    event_time = os.getenv("EVENT_TIME")
    date_object = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
    event_timestamp = date_object.timestamp()

    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        imms_env = _env
    elif _env == "prod":
        imms_env = "prod"
    else:
        # for temporary envs like pr-xx or user workspaces
        imms_env = "internal-dev"

    source_bucket = os.getenv("SOURCE_BUCKET_NAME")
    destination_bucket = os.getenv("DESTINATION_BUCKET_NAME")
    object_key = os.getenv("OBJECT_KEY")
    return BatchData(
        batch_id=str(uuid.uuid4()),
        source_bucket=source_bucket,
        destination_bucket=destination_bucket,
        object_key=object_key,
        event_id=os.getenv("EVENT_ID"),
        event_timestamp=event_timestamp,
        process_timestamp=time.time(),
        environment=imms_env
    )


def batch_processing(s3_client, secret_client):
    batch = _make_batch_data()
    logging.log(logging.WARNING,
                {"type": "batch_start", "message": "a new batch processing has started", **batch.__dict__})

    cache = Cache(directory="/tmp")
    auth = AppRestrictedAuth(
        service=Service.IMMUNIZATION,
        secret_manager_client=secret_client,
        environment=batch.environment,
        cache=cache)

    api = ImmunizationApi(authenticator=auth, environment=batch.environment)

    s3_resp = s3_client.get_object(Bucket=batch.source_bucket, Key=batch.object_key)
    parser = DataParser(s3_resp["Body"])
    transformer = DataRecordTransformer()

    report_transformer = ReportEntryTransformer()
    s3_upload = S3FixedBufferStream(s3_client=s3_client, bucket=batch.destination_bucket, key=batch.object_key)
    report_gen = ReportGenerator(transformer=report_transformer, s3_stream=s3_upload)
    processor = BatchProcessor(
        batch_data=batch,
        parser=parser,
        row_transformer=transformer,
        api=api,
        report_generator=report_gen)

    try:
        processor.process()
    except Exception as e:
        data = {"type": "batch_error", "error_type": "unhandled",
                "message": f"An unhandled error happened during batch processing: {e}",
                **batch.__dict__}
        logging.log(logging.ERROR, data)


def main():
    boto_config = Config(region_name="eu-west-2")
    secrets_manager_client = boto3.client("secretsmanager", config=boto_config)
    s3_client = boto3.client("s3", config=boto_config)

    batch_processing(s3_client=s3_client, secret_client=secrets_manager_client)


if __name__ == '__main__':
    main()
