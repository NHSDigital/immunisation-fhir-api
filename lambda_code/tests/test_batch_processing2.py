import os
import sys
import unittest
from unittest.mock import MagicMock, call

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../src")

from services import ImmunisationApi, S3Service
from batch_processing_handler import batch_processing

# from lambda_code.src.services import ImmunisationApi, S3Service

source_bucket = "source-bucket"
destination_bucket = "destination-bucket"
csv_file_name = "data.csv"
csv_file_path = (
    f"{os.path.dirname(os.path.abspath(__file__))}/sample_data/{csv_file_name}"
)

sample_event = {
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": source_bucket,
                    "ownerIdentity": {"principalId": "A1XQJU98VTYE4Z"},
                    "arn": f"arn:aws:s3:::{source_bucket}",
                },
                "object": {
                    "key": csv_file_name,
                    "size": 1905,
                    "eTag": "7f3245332944742660f51cee091db9dc",
                    "sequencer": "006537C305E1353ABE",
                },
            },
        }
    ]
}


class TestBatchProcessing(unittest.TestCase):
    def setUp(self):
        self.sample_csv = ["field1", "field2"]
        self.imms_api = ImmunisationApi("https://example.com")
        self.s3_service = S3Service()
        self.event = sample_event
        self.context = {}

    def test_process_csv(self):
        # Given
        self.s3_service.get_s3_object = MagicMock(return_value=self.sample_csv)
        response_ok = {"statusCode": 200}
        self.imms_api.post_event = MagicMock(return_value=response_ok)
        #  When
        batch_processing(self.event, self.context, self.s3_service, self.imms_api)
        # Then
        self.s3_service.get_s3_object.assert_called_once_with(
            source_bucket, csv_file_name
        )
        self.imms_api.post_event.assert_has_calls([call("field1"), call("field2")])

    def test_create_error_report(self):
        # Given
        self.s3_service.get_s3_object = MagicMock(return_value=self.sample_csv)
        self.s3_service.write_s3_object = MagicMock()
        response_error = {"statusCode": 400}
        self.imms_api.post_event = MagicMock(return_value=response_error)
        #  When
        batch_processing(self.event, self.context, self.s3_service, self.imms_api)
        # Then
        self.s3_service.write_s3_object.assert_called_once_with(
            destination_bucket, csv_file_name, ["error", "error"]
        )
