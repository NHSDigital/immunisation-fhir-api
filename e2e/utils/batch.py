import io
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, OrderedDict, Tuple

"""Every thing you need to create a batch file and upload it to s3"""

# example headers for the batch file
base_headers = [
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
    "LOCATION_CODE_TYPE_URI",
]

# example to populate a base row with
base_value = [
    "9726811104",
    "HELENA",
    "GANDY",
    "19730409",
    "9",
    "RG1 7YE",
    "20240221T141951",
    "RVVKC",
    "001_COVID_4_1_Positive_First_Dose_20240222164519",
    "https://evahealth.co.uk/identifier/vacc",
    "new",
    "Ellena",
    "O'Reilly",
    "2038243",
    "https://fhir.hl7.org.uk/Id/gphc-number",
    "DEFAULT_JOB_ROLE_NAME",
    "20240221",
    "TRUE",
    "X99999",
    "1324681000000101",
    "Administration of first dose of SARS-CoV-2 (severe acute respiratory syndrome coronavirus 2) vaccine",
    "",
    "",
    "FALSE",
    "",
    "",
    1,
    "39326911000001101",
    "Spikevax COVID-19 mRNA Vaccine 0.1mg/0.5mL dose dispersion for injection multidose vials (Moderna, Inc)",
    "Moderna",
    "BN1231231AW",
    "20240303",
    "368208006",
    "Left upper arm structure (body structure)",
    "78421000",
    "Intramuscular route (qualifier value)",
    "0.5",
    "258773002",
    "Milliliter (qualifier value)",
    "443684005",
    "Disease Outbreak (event)",
    "02",
    "Number present but not traced",
    "https://fhir.nhs.uk/Id/ods-organization-code",
    "528458",
    "https://nivs.ardengemcsu.nhs.uk_COVID",
    "762911000000102",
    "Informed consent given for treatment (finding)",
    "413294000",
    "Community health services (qualifier value)",
    "192.168.0.56",
    "634165",
    "bloggsj21",
    "joebloggs21@test.net",
    "20240221T17193000",
    "RJC02",
    "https://fhir.nhs.uk/Id/ods-organization-code",
]

base_record = OrderedDict[str, str](zip(base_headers, base_value))


def _make_header(stream: io.BytesIO, headers: List[str]):
    headers_str = "|".join(headers)
    stream.write(headers_str.encode())
    stream.write(b"\n")


def _make_row_entry(record: OrderedDict[str, str], stream: io.BytesIO):
    row_str = "|".join(f'"{v}"' for v in record.values())
    row_str += "\n"
    stream.write(row_str.encode())


def _get_terraform_output(output_name: str) -> str:
    # NOTE: We need to run make target to get output values from our deployment
    terraform_dir = f"{os.path.abspath(os.path.dirname(__file__))}/../../terraform"
    terraform = shutil.which("terraform")
    output = subprocess.run(
        [terraform, f"-chdir={terraform_dir}", "output", "-raw", output_name],
        cwd=terraform_dir,
        capture_output=True,
        env={"AWS_PROFILE": "apim-dev"},
        text=True,
    )
    if output.returncode != 0:
        raise RuntimeError(
            f"Error getting terraform output {output_name}: {output.stderr}"
        )
    return output.stdout.strip()


def get_s3_source_name():
    return _get_terraform_output("batch_source_bucket")


def get_s3_destination_name():
    return _get_terraform_output("batch_destination_bucket")


def get_cluster_name():
    return _get_terraform_output("batch_cluster_name")


def download_report_file(s3_client, bucket, key) -> str:
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    return data.decode("utf-8")


@dataclass
class CtlData:
    from_dts: str
    to_dts: str

    def to_xml(self) -> str:
        return f"""
<DTSControl>
    <Version>1.0</Version>
    <AddressType>DTS</AddressType>
    <MessageType>DATA</MessageType>
    <From_DTS>{self.from_dts}</From_DTS>
    <To_DTS>{self.to_dts}</To_DTS>
    <Subject>file_type=csv;sender_id=NBORetry</Subject>
    <LocalId>Tester01</LocalId>
    <DTSId>MPTREQ_20181114134908</DTSId>
    <Compress>Y</Compress>
    <Encrypted>N</Encrypted>
    <WorkflowId>VACCINATIONS_DAILY_COVID_4</WorkflowId>
    <ProcessId></ProcessId>
    <DataChecksum></DataChecksum>
    <IsCompressed>Y</IsCompressed>
    <AllowChunking>Y</AllowChunking>
</DTSControl>
"""


class CtlFile:
    def __init__(self, ctl_data: CtlData):
        self.stream = io.BytesIO()
        self.ctl_data = ctl_data
        self.stream.write(self.ctl_data.to_xml().encode())

    # def upload_to_s3(self, s3_client, bucket, key):
    #     self.stream.seek(0)
    #     s3_client.upload_fileobj(self.stream, bucket, key)
    #     self.stream.close()

    def upload_to_s3(self, s3_client, bucket):
        self.stream.seek(0)
        s3_client.upload_fileobj(self.stream, bucket)
        self.stream.close()


class BatchFile:
    # each record holds a message and a record
    records: List[Tuple[str, OrderedDict[str, str]]] = []
    headers: List[str] = []

    def __init__(self, headers: List[str] = None):
        if headers is None:
            headers = base_headers
        self.headers = headers
        self.stream = io.BytesIO()

        _make_header(self.stream, self.headers)

    def add_record(self, record: OrderedDict[str, str], msg: str = ""):
        if len(record.values()) != len(self.headers):
            raise ValueError("record does not have the correct number of fields")
        if self.stream.closed:
            raise ValueError("batch file is closed")
        self.records.append((msg, record))
        _make_row_entry(record, self.stream)

    # def upload_to_s3(self, s3_client, bucket, key):
    #     self.stream.seek(0)
    #     s3_client.upload_fileobj(
    #         self.stream, bucket, key, ExtraArgs={"ContentType": "text/plain"}
    #     )
    #     self.stream.close()

    def upload_to_s3(self, s3_client, bucket):
        self.stream.seek(0)
        s3_client.upload_fileobj(
            self.stream, bucket, ExtraArgs={"ContentType": "text/plain"}
        )
        self.stream.close()
