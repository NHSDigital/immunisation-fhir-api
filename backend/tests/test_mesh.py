import copy
import json
import os
import unittest

import boto3
from mesh import (
    MeshInputHandler,
    MeshOutputHandler,
    MeshCsvParser,
    MeshImmunisationReportEntry,
)
from moto import mock_s3

sample_event = {
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": "a-bucket",
                    "ownerIdentity": {"principalId": "A1XQJU98VTYE4Z"},
                    "arn": f"arn:aws:s3:::a-bucket",
                },
                "object": {
                    "key": "a-key",
                    "size": 1905,
                    "eTag": "7f3245332944742660f51cee091db9dc",
                    "sequencer": "006537C305E1353ABE",
                },
            },
        }
    ]
}


def create_an_event_record(bucket_name, key):
    """create ONE fake record and NOT the entire event object"""
    record = copy.copy(sample_event)["Records"][0]
    record["s3"]["bucket"]["name"] = bucket_name
    record["s3"]["object"]["key"] = key

    return record


def create_a_bucket(name):
    s3_client = boto3.resource("s3", region_name="eu-west-2")
    return s3_client.create_bucket(
        Bucket=name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
    )


class TestMeshInputHandler(unittest.TestCase):
    def setUp(self):
        self.bucket = "input-bucket"
        self.key = "input-key"
        self.content = "input-content"
        self.event_record = create_an_event_record(self.bucket, self.key)

        self.mesh_input = MeshInputHandler(self.event_record)

    @mock_s3
    def test_get_event_content(self):
        input_bucket = create_a_bucket(self.bucket)
        input_bucket.put_object(Body=self.content, Key=self.key)

        data = self.mesh_input.get_event_content()

        self.assertEqual(data, self.content)


class TestMeshOutputHandler(unittest.TestCase):
    def setUp(self):
        self.bucket = "output-bucket"
        self.key = "output-key"
        self.content = "output-content"

        self.mesh_output = MeshOutputHandler(self.bucket, self.key)

    @mock_s3
    def test_write_to_s3(self):
        output_bucket = create_a_bucket(self.bucket)
        records = [
            MeshImmunisationReportEntry("error1"),
            MeshImmunisationReportEntry("error2"),
        ]
        # TODO: create a method here to read the object. make this to test if write_report is working.
        self.mesh_output.write_report(records)


class TestMeshCsvParser(unittest.TestCase):
    """Test the MeshCsvParser class"""

    def setUp(self):
        self.data_path = f"{os.path.dirname(os.path.abspath(__file__))}/sample_data"
        self.csv_file_name = "test_mesh_data.csv"
        self.csv_file_path = f"{self.data_path}/{self.csv_file_name}"
        self.successful_happy_output_file_name = "successful_happy_output.json"
        self.successful_happy_output_file_path = (
            f"{self.data_path}/{self.successful_happy_output_file_name}"
        )
        self.failed_happy_output_file_name = "failed_happy_output.json"
        self.failed_happy_output_file_path = (
            f"{self.data_path}/{self.failed_happy_output_file_name}"
        )

        with open(self.csv_file_path, "r", encoding="utf-8") as data:
            self.sample_csv = data.read()

        self.successful_happy_output_file_path = (
            f"{self.data_path}/{self.successful_happy_output_file_name}"
        )
        with open(
            self.successful_happy_output_file_path, "r", encoding="utf-8"
        ) as data:
            self.successful_happy_output = data.read()

        with open(self.failed_happy_output_file_path, "r", encoding="utf-8") as data:
            self.failed_happy_output = data.read()

    def test_parse_csv(self):
        """
        Test that we get a ImmunizationModel object and a ImmunizationErrorModel from parsing
        the CSV
        """
        mesh_csv = MeshCsvParser(self.sample_csv)
        records = mesh_csv.parse()
        self.assertEqual(len(records), 2)

    def test_successful_immunizations_happy_output(self):
        """Test that the successful immunization record is formatted correctly"""
        mesh_csv = MeshCsvParser(self.sample_csv)
        immunisation_records, _ = mesh_csv.parse()
        immunisation_record_json = json.dumps(
            immunisation_records[0].dict(), indent=4, default=str
        )

        self.assertDictEqual(
            json.loads(immunisation_record_json),
            json.loads(self.successful_happy_output),
        )

    def test_failed_immunizations_happy_output(self):
        """Test that the failed immunization record is formatted correctly"""
        mesh_csv = MeshCsvParser(self.sample_csv)
        _, failed_records = mesh_csv.parse()
        failed_record_json = json.dumps(failed_records[0].dict(), indent=4, default=str)

        self.assertDictEqual(
            json.loads(failed_record_json), json.loads(self.failed_happy_output)
        )
