import os
from unittest import TestCase
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws


def invoke_lambda(file_key: str):
    # Local import so that globals can be mocked
    from converter import lambda_handler
    return lambda_handler(
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

        result = invoke_lambda("test-csv-file.csv")
        self.assertEqual(result["statusCode"], 200)

        get_target_response = s3.get_object(Bucket="destination-bucket", Key="overridden-filename.csv")
        body = get_target_response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

        with self.assertRaises(ClientError) as e:
            s3.head_object(Bucket="source-bucket", Key="test-csv-file.csv")
        self.assertEqual(e.exception.response["Error"]["Code"], "404")

        head_archive_response = s3.head_object(Bucket="source-bucket", Key="archive/test-csv-file.csv")
        assert head_archive_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_non_multipart_content_type_without_mesh_metadata(self):
        s3 = boto3.client("s3", region_name="eu-west-2")
        s3.put_object(
            Bucket="source-bucket",
            Key="test-csv-file.csv",
            Body="some CSV content".encode("utf-8"),
            ContentType="text/csv",
        )

        result = invoke_lambda("test-csv-file.csv")
        self.assertEqual(result["statusCode"], 200)

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"

    def test_multipart_content_type(self):
        cases = [
            (
                "standard",
                "\r\n".join([
                    "",
                    "--12345678",
                    'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
                    "Content-Type: text/csv",
                    "",
                    "some CSV content",
                    "--12345678--",
                    ""
                ])
            ),
            (
                "missing initial newline",
                "\r\n".join([
                    "--12345678",
                    'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
                    "Content-Type: text/csv",
                    "",
                    "some CSV content",
                    "--12345678--",
                    ""
                ])
            ),
            (
                "missing final newline",
                "\r\n".join([
                    "",
                    "--12345678",
                    'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
                    "Content-Type: text/csv",
                    "",
                    "some CSV content",
                    "--12345678--",
                ])
            ),
            (
                "multiple parts",
                "\r\n".join([
                    "",
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
            )
        ]
        for msg, body in cases:
            with self.subTest(msg=msg, body=body):
                s3 = boto3.client("s3", region_name="eu-west-2")
                s3.put_object(
                    Bucket="source-bucket",
                    Key="test-dat-file.dat",
                    Body=body.encode("utf-8"),
                    ContentType="multipart/form-data; boundary=12345678",
                )

                result = invoke_lambda("test-dat-file.dat")
                self.assertEqual(result["statusCode"], 200)

                response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
                body = response["Body"].read().decode("utf-8")
                assert body == "some CSV content"
                content_type = response["ContentType"]
                assert content_type == "text/csv"

    def test_multipart_content_type_without_filename_in_headers(self):
        cases = [
            (
                "no filename in header",
                "\r\n".join([
                    "",
                    "--12345678",
                    'Content-Disposition: form-data',
                    "Content-Type: text/csv",
                    "",
                    "some CSV content",
                    "--12345678--",
                    ""
                ])
            ),
            (
                "no header",
                "\r\n".join([
                    "",
                    "--12345678",
                    "",
                    "some CSV content",
                    "--12345678--",
                    ""
                ])
            )
        ]
        for msg, body in cases:
            with self.subTest(msg=msg, body=body):
                s3 = boto3.client("s3", region_name="eu-west-2")
                s3.put_object(
                    Bucket="source-bucket",
                    Key="test-dat-file.dat",
                    Body=body.encode("utf-8"),
                    ContentType="multipart/form-data; boundary=12345678",
                )

                result = invoke_lambda("test-dat-file.dat")
                self.assertEqual(result["statusCode"], 200)

                response = s3.get_object(Bucket="destination-bucket", Key="test-dat-file.dat")
                body = response["Body"].read().decode("utf-8")
                assert body == "some CSV content"

    def test_multipart_content_type_without_content_type_in_headers(self):
        body = "\r\n".join([
            "",
            "--12345678",
            'Content-Disposition: form-data; name="File"; filename="test-csv-file.csv"',
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

        result = invoke_lambda("test-dat-file.dat")
        self.assertEqual(result["statusCode"], 200)

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content"
        content_type = response["ContentType"]
        assert content_type == "application/octet-stream"

    def test_multipart_content_type_with_unix_line_endings(self):
        body = "\r\n".join([
            "",
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

        result = invoke_lambda("test-dat-file.dat")
        self.assertEqual(result["statusCode"], 200)

        response = s3.get_object(Bucket="destination-bucket", Key="test-csv-file.csv")
        body = response["Body"].read().decode("utf-8")
        assert body == "some CSV content\nsplit across\nmultiple lines"

    def test_unexpected_end_of_file(self):
        for msg, body in [
            ("before first part", ""),
            ("in headers", "--12345678\r\n"),
            ("in body", "--12345678\r\n\r\n"),
        ]:
            with self.subTest(msg=msg, body=body):
                s3 = boto3.client("s3", region_name="eu-west-2")
                s3.put_object(
                    Bucket="source-bucket",
                    Key="test-dat-file.dat",
                    Body=body.encode("utf-8"),
                    ContentType="multipart/form-data; boundary=12345678",
                )

                result = invoke_lambda("test-dat-file.dat")
                self.assertEqual(result["statusCode"], 500)

                with self.assertRaises(ClientError) as e:
                    s3.head_object(Bucket="destination-bucket", Key="test-csv-file.csv")
                self.assertEqual(e.exception.response["Error"]["Code"], "404")
