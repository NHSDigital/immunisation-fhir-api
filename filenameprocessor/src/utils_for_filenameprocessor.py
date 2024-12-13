"""Utils for filenameprocessor lambda"""

from csv import DictReader
from io import StringIO
from constants import Constants
from clients import s3_client


def get_created_at_formatted_string(bucket_name: str, file_key: str) -> str:
    """Get the created_at_formatted_string from the response"""
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response["LastModified"].strftime("%Y%m%dT%H%M%S00")


def get_csv_content_dict_reader(bucket_name: str, file_key: str) -> DictReader:
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


def identify_supplier(ods_code: str) -> str:
    """
    Identifies the supplier from the ods code using the mapping.
    Defaults to empty string if ODS code isn't found in the mappings.
    """
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code, "")
