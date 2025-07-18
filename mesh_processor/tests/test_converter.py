import os
from unittest import TestCase
from unittest.mock import patch

import boto3
from moto import mock_aws


def invoke_lambda(file_key: str):
    # Local import so that globals can be mocked
    from converter import lambda_handler
    lambda_handler(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "source-bucket"},
                        "object": {"key": file_key}
                    }
                }
            ]
        },
        {}
    )


@mock_aws
@patch.dict(os.environ, {"DESTINATION_BUCKET_NAME": "destination-bucket"})
class TestLambdaHandler(TestCase):
    def setUp(self):
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.create_bucket(Bucket="source-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        s3.create_bucket(Bucket="destination-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

    def test_non_multipart_content_type(self):
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-csv-file.csv",
            Body="some CSV content".encode("utf-8"),
            ContentType="text/csv",
            Metadata={
                "mex-filename": "overridden-filename.csv",
            }
        )

        invoke_lambda("test-csv-file.csv")

        response = s3.get_object(Bucket="destination-bucket", Key="overridden-filename.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_non_multipart_content_type_no_mesh_metadata(self):
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-csv-file.csv",
            Body="some CSV content".encode("utf-8"),
            ContentType="text/csv",
        )

        invoke_lambda("test-csv-file.csv")

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type(self):
        body = "\r\n".join([
            "--12345678",
            'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
            "Content-Type: text/csv",
            "",
            "some CSV content",
            "--12345678--",
            ""
        ])
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-dat-file.dat",
            Body=body.encode("utf-8"),
            ContentType="multipart/form-data; boundary=12345678",
        )

        invoke_lambda("test-dat-file.dat")

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type_multiple_parts(self):
        body = "\r\n".join([
            "--12345678",
            'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
            "Content-Type: text/csv",
            "",
            "some CSV content",
            "--12345678",
            'Content-Disposition: form-data; name="File"; filename="test-ignored-file"',
            "Content-Type: text/plain",
            "",
            "some ignored content",
            "--12345678--",
            ""
        ])
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-dat-file.dat",
            Body=body.encode("utf-8"),
            ContentType="multipart/form-data; boundary=12345678",
        )

        invoke_lambda("test-dat-file.dat")

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type_without_filename(self):
        body = "\r\n".join([
            "--12345678",
            'Content-Disposition: form-data',
            "Content-Type: text/csv",
            "",
            "some CSV content",
            "--12345678--",
            ""
        ])
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-dat-file.dat",
            Body=body.encode("utf-8"),
            ContentType="multipart/form-data; boundary=12345678",
        )

        invoke_lambda("test-dat-file.dat")

        response = s3.get_object(Bucket="destination-bucket", Key="test-dat-file.dat")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type_without_headers(self):
        body = "\r\n".join([
            "--12345678",
            "",
            "some CSV content",
            "--12345678--",
            ""
        ])
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-dat-file.dat",
            Body=body.encode("utf-8"),
            ContentType="multipart/form-data; boundary=12345678",
        )

        invoke_lambda("test-dat-file.dat")

        response = s3.get_object(Bucket="destination-bucket", Key="test-dat-file.dat")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type_with_unix_line_endings(self):
        body = "\r\n".join([
            "--12345678",
            'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
            "Content-Type: text/csv",
            "",
            "some CSV content\nsplit across\nmultiple lines",
            "--12345678--",
            ""
        ])
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-dat-file.dat",
            Body=body.encode("utf-8"),
            ContentType="multipart/form-data; boundary=12345678",
        )

        invoke_lambda("test-dat-file.dat")

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content\nsplit across\nmultiple lines"
