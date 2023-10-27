from dataclasses import dataclass
from model_to_fhir import convert_to_fhir
from csv_to_model import read_csv_to_immunizations
from datetime import datetime
from icecream import ic

import boto3


@dataclass
class MeshImmunisationReportEntry:
    error: str

    # TODO: The caller will call this to convert this object into one line in the report.
    # Probably it'd be better to override __str__ method. For now just create a string like f"{self.error}". The caller
    # generates the full report by calling this method for each entry and append the result. The final result will be the
    # the content of the destination bucket(error report)
    def to_report_entry(self):
        pass


# TODO: This is just a POC. See if you can bring logic from previous work. It doesn't have to be a dataclass.
# As long as we convert csv into some object (dataclass/dic/etc) we're good.


class MeshImmunisationRecord:
    # TODO: This class should have a to_immunisation_fhir() method. So we can convert a csv record into Fhir object
    # convert it to Almas's FHIR object or fhir.resource. For now anything that makes the POST call happy will do.
    def to_immunisation_fhir(self):
        # pass
        return convert_to_fhir(self)


# This object captures any kind of error. Either validation of API call errors. This means at end of batch processing
# we will end up with a list of errors. We don't write this error directly into destination bucket because,
# the destination bucket i.e. MESH report has its own mapping requirement.
# So, this class has to have a to_mesh_immunisation_report_entry() method
@dataclass
class MeshImmunisationError:
    message: str

    def to_mesh_immunisation_report_entry(self) -> MeshImmunisationReportEntry:
        pass


class MeshCsvParser:
    def __init__(self, content):
        self.content = content

    def parse(self) -> ([MeshImmunisationRecord], [MeshImmunisationError]):
        """Parse every CSV record and return a tuple
        first item is a list of successful records and second one is a list of errors
        """
        # TODO: parse the content line-by-line and generate two lists. One list is the record and one list is the error
        # For example 20 lines of CSV will produce 15 MeshImmunisationRecord and 4 MeshImmunisationError + 1 field row
        # For now assume every record is ok and return an empty list for errors
        immunization_records = read_csv_to_immunizations(self.content)
        ic(immunization_records)
        return (
            immunization_records
            # [MeshImmunisationRecord("", "", ""), MeshImmunisationRecord("", "", "")],
            # [MeshImmunisationError("error1"), MeshImmunisationError("error2")],
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
