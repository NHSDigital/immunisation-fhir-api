import csv
import uuid
from datetime import datetime, timezone

import pandas as pd
from clients import logger
from errors import DynamoDBMismatchError
from vax_suppliers import OdsVax, TestPair

from constants import (
    ACK_BUCKET,
    RAVS_URI,
    ActionFlag,
    BusRowResult,
    DestinationType,
    Operation,
    OperationOutcome,
)
from utils import (
    aws_cleanup,
    create_row,
    fetch_pk_and_operation_from_dynamodb,
    get_file_content_from_s3,
    poll_s3_file_pattern,
    validate_fatal_error,
)


class TestAction:
    def __init__(
        self,
        action: ActionFlag,
        expected_header_response_code=BusRowResult.SUCCESS,
        expected_operation_outcome="",
    ):
        self.action = action
        self.expected_header_response_code = expected_header_response_code
        self.expected_operation_outcome = expected_operation_outcome


class TestCase:
    def __init__(self, scenario: dict):
        self.name: str = scenario.get("name", "Unnamed Test Case")
        self.description: str = scenario.get("description", "")
        self.ods_vax: OdsVax = scenario.get("ods_vax")
        self.actions: list[TestAction] = scenario.get("actions", [])
        self.ods = self.ods_vax.ods_code
        self.vax = self.ods_vax.vax
        self.dose_amount: float = scenario.get("dose_amount", 0.5)
        self.inject_cp1252 = scenario.get("create_with_cp1252_encoded_character", False)
        self.header = scenario.get("header", "NHS_NUMBER")
        self.version = scenario.get("version", 5)
        self.operation_outcome = scenario.get("operation_outcome", "")
        self.enabled = scenario.get("enabled", False)
        self.ack_keys = {DestinationType.INF: None, DestinationType.BUS: None}
        # initialise attribs to be set later
        self.key = None  # S3 key of the uploaded file
        self.file_name = None  # name of the generated CSV file
        self.identifier = None  # unique identifier of subject in the CSV file rows

    def get_poll_destinations(self, pending: bool) -> bool:
        # loop through keys in test (inf and bus)
        for ack_key in self.ack_keys.keys():
            if not self.ack_keys[ack_key]:
                found_ack_key = self.poll_destination(ack_key)
                if found_ack_key:
                    self.ack_keys[ack_key] = found_ack_key
                else:
                    pending = True
        return pending

    def poll_destination(self, ack_prefix: DestinationType):
        """Poll the ACK_BUCKET for an ack file that contains the input_file_name as a substring."""
        input_file_name = self.file_name
        filename_without_ext = input_file_name[:-4] if input_file_name.endswith(".csv") else input_file_name
        search_pattern = f"{ack_prefix}{filename_without_ext}"
        return poll_s3_file_pattern(ack_prefix, search_pattern)

    def check_final_success_action(self):
        desc = f"{self.name} - outcome"
        outcome = self.operation_outcome
        dynamo_pk, operation, is_reinstate = fetch_pk_and_operation_from_dynamodb(self.get_identifier_pk())

        expected_operation = Operation.CREATE if outcome == ActionFlag.CREATE else outcome
        if operation != expected_operation:
            raise DynamoDBMismatchError(
                (
                    f"{desc}. Final Event Table Operation: Mismatch - DynamoDB Operation '{operation}' "
                    f"does not match operation requested '{outcome}' (3)"
                )
            )

    def get_identifier_pk(self):
        if not self.identifier:
            raise Exception("Identifier not set. Generate the CSV file first.")
        return f"{RAVS_URI}#{self.identifier}"

    def check_bus_file_content(self):
        desc = f"{self.name} - bus"
        content = get_file_content_from_s3(ACK_BUCKET, self.ack_keys[DestinationType.BUS])
        reader = csv.DictReader(content.splitlines(), delimiter="|")
        rows = list(reader)

        for i, row in enumerate(rows):
            response_code = self.actions[i].expected_header_response_code
            operation_outcome = self.actions[i].expected_operation_outcome
            if response_code and "HEADER_RESPONSE_CODE" in row:
                row_HEADER_RESPONSE_CODE = row["HEADER_RESPONSE_CODE"].strip()
                assert row_HEADER_RESPONSE_CODE == response_code, (
                    f"{desc}.Row {i} expected HEADER_RESPONSE_CODE '{response_code}', "
                    f"but got '{row_HEADER_RESPONSE_CODE}'"
                )
            if operation_outcome and "OPERATION_OUTCOME" in row:
                row_OPERATION_OUTCOME = row["OPERATION_OUTCOME"].strip()
                assert row_OPERATION_OUTCOME.startswith(operation_outcome), (
                    f"{desc}.Row {i} expected OPERATION_OUTCOME '{operation_outcome}', but got '{row_OPERATION_OUTCOME}'"
                )
            elif row_HEADER_RESPONSE_CODE == "Fatal Error":
                validate_fatal_error(desc, row, i, operation_outcome)

    def generate_csv_file(self):
        self.file_name = self.get_file_name(self.vax, self.ods, self.version)
        logger.info(f'Test "{self.name}" File {self.file_name}')
        data = []
        self.identifier = str(uuid.uuid4())
        for action in self.actions:
            row = create_row(
                self.identifier,
                self.dose_amount,
                action.action,
                self.header,
                self.inject_cp1252,
            )
            logger.info(f" > {action.action} - {self.vax}/{self.ods} - {self.identifier}")
            data.append(row)
        df = pd.DataFrame(data)

        df.to_csv(self.file_name, index=False, sep="|", quoting=csv.QUOTE_MINIMAL)

    def get_file_name(self, vax_type, ods, version="5"):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S00")
        return f"{vax_type}_Vaccinations_v{version}_{ods}_{timestamp}.csv"

    def cleanup(self):
        aws_cleanup(self.key, self.identifier, self.ack_keys)


def create_test_cases(test_case_dict: dict) -> list[TestCase]:
    """Initialize test cases from a dictionary."""
    return [TestCase(name) for name in test_case_dict]


def enable_tests(test_cases: list[TestCase], names: list[str]) -> None:
    """Enable only the test cases with the given names."""
    for name in names:
        for test in test_cases:
            if test.name == name:
                test.enabled = True
                break
        else:
            raise Exception(f"Test case with name '{name}' not found.")


def generate_csv_files(test_cases: list[TestCase]) -> list[TestCase]:
    """Generate CSV files for all enabled test cases."""
    ret = []
    for test in test_cases:
        if test.enabled:
            test.generate_csv_file()
            ret.append(test)


scenarios = {
    "dev": [
        {
            "name": "Successful Create",
            "ods_vax": TestPair.E8HA94_COVID_CUD,
            "operation_outcome": ActionFlag.CREATE,
            "actions": [TestAction(ActionFlag.CREATE)],
            "description": "Successful Create",
        },
        {
            "name": "Successful Update",
            "description": "Successful Create,Update",
            "ods_vax": TestPair.DPSFULL_COVID_CRUDS,
            "operation_outcome": ActionFlag.UPDATE,
            "actions": [TestAction(ActionFlag.CREATE), TestAction(ActionFlag.UPDATE)],
        },
        {
            "name": "Successful Delete",
            "description": "Successful Create,Update, Delete",
            "ods_vax": TestPair.V0V8L_FLU_CRUDS,
            "operation_outcome": ActionFlag.DELETE_LOGICAL,
            "actions": [
                TestAction(ActionFlag.CREATE),
                TestAction(ActionFlag.DELETE_LOGICAL),
            ],
        },
        {
            "name": "Failed Update",
            "description": "Failed Update - resource does not exist",
            "ods_vax": TestPair.V0V8L_3IN1_CRUDS,
            "actions": [
                TestAction(
                    ActionFlag.UPDATE,
                    expected_header_response_code=BusRowResult.FATAL_ERROR,
                    expected_operation_outcome=OperationOutcome.IMMS_NOT_FOUND,
                )
            ],
            "operation_outcome": ActionFlag.NONE,
        },
        {
            "name": "Failed Delete",
            "description": "Failed Delete - resource does not exist",
            "ods_vax": TestPair.X26_MMR_CRUDS,
            "actions": [
                TestAction(
                    ActionFlag.DELETE_LOGICAL,
                    expected_header_response_code=BusRowResult.FATAL_ERROR,
                    expected_operation_outcome=OperationOutcome.IMMS_NOT_FOUND,
                )
            ],
            "operation_outcome": ActionFlag.NONE,
        },
        {
            "name": "Create with 1252 char",
            "description": "Create with 1252 char",
            "ods_vax": TestPair.YGA_MENACWY_CRUDS,
            "operation_outcome": ActionFlag.CREATE,
            "actions": [TestAction(ActionFlag.CREATE)],
            "create_with_cp1252_encoded_character": True,
        },
    ],
    "ref": [],
}
