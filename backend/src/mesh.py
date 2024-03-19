from dataclasses import dataclass

import boto3
from csv_to_model import read_csv_to_model
from models.csv_immunisation import CsvImmunisationModel
from models.failures import CsvImmunisationErrorModel


@dataclass
class MeshImmunisationReportEntry:
    error: str

    # TODO: The caller will call this to convert this object into one line in the report.
    # Probably it'd be better to override __str__ method. For now just create a string like f"{self.error}". The caller
    # generates the full report by calling this method for each entry and append the result. The final result will be the
    # the content of the destination bucket(error report)
    def to_report_entry(self):
        pass


class MeshCsvParser:
    """Parse a CSV file and return a list of ImmunisationModel and ImmunisationErrorModel"""

    def __init__(self, content):
        self.content = content

    def parse(self) -> ([CsvImmunisationModel], [CsvImmunisationErrorModel]):
        """Parse every CSV record and return a tuple
        first item is a list of successful records and second one is a list of errors
        """
        immunisation_records, failed_records = read_csv_to_model(self.content)
        return (
            immunisation_records,
            failed_records,
        )


class MeshInputHandler:
    # it's one single Record from the event
    def __init__(self, s3_event_record):
        self.s3_event_record = s3_event_record
        # validation is required for the name of the bundle.
        #  In our case name of the bundle is the csv file name i.e. source object's name
        # TODO: Throw exception if name is not valid.
        #  Exception handler (caller site) should create file.bad in the destination bucket

    def get_event_content(self) -> str:
        bucket = self.s3_event_record["s3"]["bucket"]["name"]
        key = self.s3_event_record["s3"]["object"]["key"]
        client = boto3.client("s3")
        resp = client.get_object(Bucket=bucket, Key=key)

        return resp["Body"].read().decode("utf-8")


class MeshOutputHandler:
    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key

    def write_report(self, report_entries: [MeshImmunisationReportEntry]):
        client = boto3.client("s3")
        # TODO: This content will be the result of  map->report_entries.to_report_entry()
        #  and appending each item to create the full report
        content = "error report"
        resp = client.put_object(Bucket=self.bucket, Key=self.key, Body=content)

        return resp


# TODO: This class must be deleted. Use MeshIn/Out instead.
#  It's still here to make tests and batch_processing_handler happy
class S3Service:
    def get_s3_object(self, bucket, key):
        client = boto3.client("s3")
        resp = client.get_object(Bucket=bucket, Key=key)

        return resp["Body"].read().decode("utf-8")

    def write_s3_object(self, bucket, key, content):
        client = boto3.client("s3")
        resp = client.put_object(Bucket=bucket, Key=key, Body=content)
        return resp
