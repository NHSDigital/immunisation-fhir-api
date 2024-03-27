import io
from collections import OrderedDict

"""Every thing you need to create a batch file and upload it to s3"""

headers = [
    "NHS_NUMBER",
    "PERSON_FORENAME",
    "PERSON_SURNAME",
    "PERSON_DOB",
    "PERSON_GENDER_CODE",
    "PERSON_POSTCODE",
    "DATE_AND_TIME",
    "SITE_CODE",
    "UNIQUE_ID",
    "UNIQUE_ID_URI",
    "ACTION_FLAG",
    "PERFORMING_PROFESSIONAL_FORENAME",
    "PERFORMING_PROFESSIONAL_SURNAME",
    "PERFORMING_PROFESSIONAL_BODY_REG_CODE",
    "PERFORMING_PROFESSIONAL_BODY_REG_URI",
    "SDS_JOB_ROLE_NAME",
    "RECORDED_DATE",
    "PRIMARY_SOURCE",
    "REPORT_ORIGIN",
    "VACCINATION_PROCEDURE_CODE",
    "VACCINATION_PROCEDURE_TERM",
    "VACCINATION_SITUATION_CODE",
    "VACCINATION_SITUATION_TERM",
    "NOT_GIVEN",
    "REASON_NOT_GIVEN_CODE",
    "REASON_NOT_GIVEN_TERM",
    "DOSE_SEQUENCE",
    "VACCINE_PRODUCT_CODE",
    "VACCINE_PRODUCT_TERM",
    "VACCINE_MANUFACTURER",
    "BATCH_NUMBER",
    "EXPIRY_DATE",
    "SITE_OF_VACCINATION_CODE",
    "SITE_OF_VACCINATION_TERM",
    "ROUTE_OF_VACCINATION_CODE",
    "ROUTE_OF_VACCINATION_TERM",
    "DOSE_AMOUNT",
    "DOSE_UNIT_CODE",
    "DOSE_UNIT_TERM",
    "INDICATION_CODE",
    "INDICATION_TERM",
    "NHS_NUMBER_STATUS_INDICATOR_CODE",
    "NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION",
    "SITE_CODE_TYPE_URI",
    "LOCAL_PATIENT_ID",
    "LOCAL_PATIENT_URI",
    "CONSENT_FOR_TREATMENT_CODE",
    "CONSENT_FOR_TREATMENT_DESCRIPTION",
    "CARE_SETTING_TYPE_CODE",
    "CARE_SETTING_TYPE_DESCRIPTION",
    "IP_ADDRESS",
    "USER_ID",
    "USER_NAME",
    "USER_EMAIL",
    "SUBMITTED_TIMESTAMP",
    "LOCATION_CODE",
    "LOCATION_CODE_TYPE_URI"
]


def _make_header(stream: io.BytesIO):
    headers_str = "|".join(headers)
    stream.write(headers_str.encode())
    stream.write(b"\n")


def _make_row_entry(record: OrderedDict[str, str], stream: io.BytesIO):
    row_str = '|'.join(f'"{v}"' for v in record.values())
    row_str += "\n"
    stream.write(row_str.encode())


class BatchFile:
    def __init__(self, stream: io.BytesIO):
        self.stream = stream
        _make_header(self.stream)
        self.closed = False

    def add_record(self, record: OrderedDict[str, str]):
        if self.closed:
            raise ValueError("Batch file is closed")
        _make_row_entry(record, self.stream)

    def close(self):
        self.stream.seek(0)
        self.closed = True

    def upload_to_s3(self, s3_client, bucket, key):
        self.close()
        s3_client.upload_fileobj(self.stream, bucket, key)
