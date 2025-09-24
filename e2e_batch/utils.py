import time
import csv
import pandas as pd
import uuid
import json
import random
import io
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from io import StringIO
from datetime import datetime, timezone
from clients import logger, s3_client, audit_table, events_table
from errors import AckFileNotFoundError, DynamoDBMismatchError
from constants import (
    ACK_BUCKET,
    FORWARDEDFILE_PREFIX,
    SOURCE_BUCKET,
    DUPLICATE,
    create_row,
    ACK_PREFIX,
    FILE_NAME_VAL_ERROR,
    HEADER_RESPONSE_CODE_COLUMN,
    RAVS_URI,
    ActionFlag,
)


def upload_file_to_s3(file_name, bucket, prefix):
    """Upload the given file to the specified bucket under the provided prefix.
    Returns the S3 key if successful, or raises an exception."""

    key = f"{prefix}{file_name}"
    try:
        with open(file_name, "rb") as f:
            response = s3_client.put_object(Bucket=bucket, Key=key, Body=f)

        # Confirm success
        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code != 200:
            raise Exception(f"Upload failed with status code: {status_code}")

        os.remove(file_name)
        return key

    except ClientError as e:
        raise Exception(f"ClientError during S3 upload: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error during file upload: {e}")


def delete_file_from_s3(bucket, key):
    """Delete the specified file (object) from the given S3 bucket.
    Returns True if deletion is successful, otherwise raises an exception."""
    try:
        response = s3_client.delete_object(Bucket=bucket, Key=key)

        # Optionally verify deletion status
        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code != 204:
            raise Exception(f"Delete failed with status code: {status_code}")

        print(f"Deleted {key}")
        return True

    except ClientError as e:
        raise Exception(f"ClientError during S3 delete: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error during file deletion: {e}")


def wait_for_ack_file(ack_prefix, input_file_name, timeout=1200):
    """Poll the ACK_BUCKET for an ack file that contains the input_file_name as a substring."""

    filename_without_ext = input_file_name[:-4] if input_file_name.endswith(".csv") else input_file_name
    if ack_prefix:
        search_pattern = f"{ACK_PREFIX}{filename_without_ext}"
        ack_prefix = ACK_PREFIX
    else:
        search_pattern = f"{FORWARDEDFILE_PREFIX}{filename_without_ext}"
        ack_prefix = FORWARDEDFILE_PREFIX
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = s3_client.list_objects_v2(Bucket=ACK_BUCKET, Prefix=ack_prefix)
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                if search_pattern in key:
                    return key
        time.sleep(5)
    raise AckFileNotFoundError(
        f"Ack file matching '{search_pattern}' not found in bucket {ACK_BUCKET} within {timeout} seconds."
    )


def get_file_content_from_s3(bucket, key):
    """Download and return the file content from S3."""

    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    return content


def check_ack_file_content(desc, content, response_code, operation_outcome, operation_requested) -> bool:
    """
    Parse and validate the acknowledgment (ACK) CSV file content.

    The function reads the content of an ACK CSV file using a pipe '|' delimiter,
    then verifies the number of rows and their content based on the provided response_code,
    operation_outcome, and operation_requested.

    Scenarios:
    - DUPLICATE scenario: If `operation_outcome` contains "The provided identifier:",
      expect exactly two rows:
        - First row: HEADER_RESPONSE_CODE = "OK" with a valid operation requested.
        - Second row: HEADER_RESPONSE_CODE = "Fatal Error" with the identifier message.

    - Normal scenarios: For each row:
        - Verify HEADER_RESPONSE_CODE matches `response_code`.
        - Verify OPERATION_OUTCOME matches `operation_outcome`.
        - Validate row content based on HEADER_RESPONSE_CODE:
            - "OK" calls `validate_ok_response`.
            - "Fatal Error" calls `validate_fatal_error`.

    Args:
        content (str): The CSV file content as a string.
        response_code (str): Expected response code (e.g., "OK" or "Fatal Error").
        operation_outcome (str): Expected operation outcome message.
        operation_requested (str): The requested operation to validate in successful rows.

    Raises:
        AssertionError: If the row count, HEADER_RESPONSE_CODE, or OPERATION_OUTCOME is incorrect.
    """

    reader = csv.DictReader(content.splitlines(), delimiter="|")
    rows = list(reader)

    if operation_outcome and DUPLICATE in operation_outcome:
        # Handle DUPLICATE scenario:
        assert len(rows) == 2, f"{desc}. Expected 2 rows for DUPLICATE scenario, got {len(rows)}"

        first_row = rows[0]
        validate_header_response_code(desc, first_row, 0, "OK")
        validate_ok_response(first_row, 0, operation_requested)

        second_row = rows[1]
        validate_header_response_code(desc, second_row, 1, "Fatal Error")
        validate_fatal_error(desc, second_row, 1, DUPLICATE)
    else:
        # Handle normal scenarios:
        for i, row in enumerate(rows):
            if response_code and "HEADER_RESPONSE_CODE" in row:
                row_HEADER_RESPONSE_CODE = row["HEADER_RESPONSE_CODE"].strip()
                assert row_HEADER_RESPONSE_CODE == response_code, (
                    f"{desc}.Row {i} expected HEADER_RESPONSE_CODE '{response_code}', "
                    f"but got '{row_HEADER_RESPONSE_CODE}'")
            if operation_outcome and "OPERATION_OUTCOME" in row:
                assert row["OPERATION_OUTCOME"].strip() == operation_outcome, (
                    f"Row {i} expected OPERATION_OUTCOME '{operation_outcome}', "
                    f"but got '{row['OPERATION_OUTCOME'].strip()}'"
                )
            if row["HEADER_RESPONSE_CODE"].strip() == "OK":
                validate_ok_response(row, i, operation_requested)
            elif row["HEADER_RESPONSE_CODE"].strip() == "Fatal Error":
                validate_fatal_error(row, i, operation_outcome)


def validate_header_response_code(desc, row, index, expected_code):
    """Ensure HEADER_RESPONSE_CODE exists and matches expected response code."""

    if "HEADER_RESPONSE_CODE" not in row:
        raise ValueError(f"Row {index + 1} does not have a 'HEADER_RESPONSE_CODE' column.")
    if row["HEADER_RESPONSE_CODE"].strip() != expected_code:
        raise ValueError(
            f"Row {index + 1}: Expected RESPONSE '{expected_code}', but found '{row['HEADER_RESPONSE_CODE']}'"
        )


def validate_fatal_error(row, index, expected_outcome):
    """Ensure OPERATION_OUTCOME matches expected outcome for Fatal Error responses."""

    if FILE_NAME_VAL_ERROR in expected_outcome:
        if expected_outcome not in row["RESPONSE_DISPLAY"].strip():
            raise ValueError(
                f"Row {index + 1}: Expected RESPONSE '{expected_outcome}', but found '{row['RESPONSE_DISPLAY']}'"
            )

    if expected_outcome not in row["OPERATION_OUTCOME"].strip():
        raise ValueError(
            f"Row {index + 1}: Expected RESPONSE '{expected_outcome}', but found '{row['OPERATION_OUTCOME']}'"
        )


def validate_ok_response(row, index, operation_requested):
    """
    Validate the LOCAL_ID format and verify that the DynamoDB primary key (PK)
    and operation match the expected values for OK responses.

    This function extracts the identifier PK from the given row, fetches the PK and
    operation from DynamoDB, and compares them against the row's IMMS_ID and the
    requested operation. If the operation is 'reinstated', additional validation
    ensures that the DynamoDB operation is 'UPDATE' and marked as reinstated.

    Args:
        row (dict): A dictionary representing a single row of the ACK file.
        index (int): The zero-based index of the row in the ACK file (for error messages).
        operation_requested (str): The expected operation (e.g., 'CREATE', 'UPDATE', 'reinstated').

    Raises:
        ValueError: If the 'LOCAL_ID' column is missing in the row.
        DynamoDBMismatchError: If the DynamoDB PK, operation, or reinstatement status does not match.
    """

    if "LOCAL_ID" not in row:
        raise ValueError(f"Row {index + 1} does not have a 'LOCAL_ID' column.")
    identifier_pk = extract_identifier_pk(row, index)
    dynamo_pk, operation, is_reinstate = fetch_pk_and_operation_from_dynamodb(identifier_pk)
    if dynamo_pk != row["IMMS_ID"]:
        raise DynamoDBMismatchError(
            f"Row {index + 1}: Mismatch - DynamoDB PK '{dynamo_pk}' does not match ACK file IMMS_ID '{row['IMMS_ID']}'"
        )

    if operation_requested == "reinstated" or operation_requested == "update-reinstated":
        if operation != "UPDATE":
            raise DynamoDBMismatchError(
                (
                    f"Row {index + 1}: Mismatch - DynamoDB Operation '{operation}' "
                    f"does not match operation requested '{operation_requested}'"
                )
            )
        if is_reinstate != "reinstated":
            raise DynamoDBMismatchError(
                (
                    f"Row {index + 1}: Mismatch - DynamoDB Operation '{is_reinstate}' "
                    f"does not match operation requested 'reinstated'"
                )
            )
    elif operation != operation_requested:
        raise DynamoDBMismatchError(
            (
                f"Row {index + 1}: Mismatch - DynamoDB Operation '{operation}' "
                f"does not match operation requested '{operation_requested}'"
            )
        )


def extract_identifier_pk(row, index):
    """Extract LOCAL_ID and convert to IdentifierPK."""
    try:
        local_id, unique_id_uri = row["LOCAL_ID"].split("^")
        return f"{unique_id_uri}#{local_id}"
    except ValueError:
        raise AssertionError(f"Row {index + 1}: Invalid LOCAL_ID format - {row['LOCAL_ID']}")


def fetch_pk_and_operation_from_dynamodb(identifier_pk):
    """
    Fetch the primary key (PK) and operation from DynamoDB using the provided IdentifierPK.

    This function queries the DynamoDB table using the 'IdentifierGSI' index to find the
    item associated with the given identifier_pk. If the item is found, it returns the PK,
    operation, and DeletedAt (if present). Otherwise, it returns 'NOT_FOUND'. If an error
    occurs during the query, it logs the error and returns 'ERROR'.

    Args:
        identifier_pk (str): The identifier key used to query DynamoDB.

    Returns:
        tuple or str: A tuple containing (PK, Operation, DeletedAt) if found,
                      'NOT_FOUND' if no item is found, or 'ERROR' if an exception occurs.

    Raises:
        Logs any exceptions encountered during the DynamoDB query.
    """
    try:
        response = events_table.query(
            IndexName="IdentifierGSI",
            KeyConditionExpression="IdentifierPK = :identifier_pk",
            ExpressionAttributeValues={":identifier_pk": identifier_pk},
        )
        if "Items" in response:
            items = response["Items"]
            if items:
                if "DeletedAt" in items[0]:
                    return (items[0]["PK"], items[0]["Operation"], items[0]["DeletedAt"])
                return (items[0]["PK"], items[0]["Operation"], None)
        return (identifier_pk, ActionFlag.NONE, None)

    except Exception as e:
        logger.error(f"Error fetching from DynamoDB: {e}")
        return "ERROR"


def validate_row_count(desc, source_file_name, ack_file_name):
    """
    Compare the row count of a file in one S3 bucket with a file in another S3 bucket.
    Raises:
        AssertionError: If the row counts do not match.
    """
    source_file_row_count = fetch_row_count(SOURCE_BUCKET, f"archive/{source_file_name}")
    ack_file_row_count = fetch_row_count(ACK_BUCKET, ack_file_name)
    assert (
        source_file_row_count == ack_file_row_count
    ), f"{desc}. Row count mismatch: Input ({source_file_row_count}) vs Ack ({ack_file_row_count})"


def fetch_row_count(bucket, file_name):
    "Fetch the row count for the file from the s3 bucket"

    response_input = s3_client.get_object(Bucket=bucket, Key=file_name)
    content_input = response_input["Body"].read().decode("utf-8")
    return sum(1 for _ in csv.reader(StringIO(content_input)))


def save_json_to_file(json_data, filename="permissions_config.json"):
    with open(filename, "w") as json_file:
        json.dump(json_data, json_file, indent=4)


def generate_csv_with_ordered_100000_rows(file_name=None):
    """
    Generate a CSV where:
    - 100 sets of (NEW → UPDATE → DELETE) are created.
    - The 100 sets are shuffled but maintain the correct order within each set.
    - The 300 shuffled sets are then randomly mixed into the 99,700 CREATE rows.
    - The final dataset ensures all NEW rows come before UPDATE and DELETE in each set.
    """
    total_rows = 100000
    special_row_count = 300
    unique_ids = [str(uuid.uuid4()) for _ in range(special_row_count // 3)]
    special_data = []

    # Generate first 300 rows as structured NEW → UPDATE → DELETE sets
    for i in range(special_row_count // 3):  # 100 sets
        new_row = create_row(
            unique_id=unique_ids[i], fore_name="PHYLIS", dose_amount="0.3", action_flag="NEW", header="NHS_NUMBER"
        )
        update_row = create_row(
            unique_id=unique_ids[i], fore_name="PHYLIS", dose_amount="0.4", action_flag="UPDATE", header="NHS_NUMBER"
        )
        delete_row = create_row(
            unique_id=unique_ids[i], fore_name="PHYLIS", dose_amount="0.1", action_flag="DELETE", header="NHS_NUMBER"
        )

        special_data.append((new_row, update_row, delete_row))  # Keep them as ordered tuples

    # Shuffle the sets (ensuring NEW is always first in each set)
    random.shuffle(special_data)

    # Flatten while maintaining NEW → UPDATE → DELETE order inside each set
    ordered_special_data = [row for set_group in special_data for row in set_group]

    # Generate remaining 99,700 rows as CREATE operations
    create_data = [
        create_row(
            unique_id=str(uuid.uuid4()), action_flag="NEW", dose_amount="0.3", fore_name="PHYLIS", header="NHS_NUMBER"
        )
        for _ in range(total_rows - special_row_count)
    ]

    # Combine 300 shuffled sets with 99,700 CREATE rows
    full_data = create_data + ordered_special_data

    # Shuffle the entire dataset while ensuring "NEW" always comes before "UPDATE" and "DELETE" in each set
    random.shuffle(full_data)

    # Sort data so that within each unique ID, "NEW" appears before "UPDATE" and "DELETE"
    full_data.sort(key=lambda x: (x["UNIQUE_ID"], x["ACTION_FLAG"] != "NEW", x["ACTION_FLAG"] == "DELETE"))

    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(full_data)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")[:-3]
    file_name = f"RSV_Vaccinations_v5_YGM41_{timestamp}.csv" if not file_name else file_name
    df.to_csv(file_name, index=False, sep="|", quoting=csv.QUOTE_MINIMAL)
    return file_name


def verify_final_ack_file(file_key):
    """Verify if the final ack file has 100,000 rows and HEADER_RESPONSE_CODE column has only 'OK' values."""
    response = s3_client.get_object(Bucket=ACK_BUCKET, Key=file_key)
    df = pd.read_csv(io.BytesIO(response["Body"].read()), delimiter="|")

    row_count = len(df)
    # Check if all HEADER_RESPONSE_CODE values are "OK"
    all_ok = df[HEADER_RESPONSE_CODE_COLUMN].nunique() == 1 and df[HEADER_RESPONSE_CODE_COLUMN].iloc[0] == "OK"
    if row_count != 100000 or not all_ok:
        raise AssertionError(
            f"Final Ack file '{file_key}' failed validation. "
            f"Row count: {row_count}"
            f"Unique HEADER_RESPONSE_CODE values: {df[HEADER_RESPONSE_CODE_COLUMN].iloc[0]}"
            f"All values OK: {all_ok}"
        )
    return True


def delete_filename_from_audit_table(filename) -> bool:

    # 1. Query the GSI to get all items with the given filename
    try:
        response = audit_table.query(
            IndexName="filename_index",
            KeyConditionExpression=Key("filename").eq(filename)
        )
        items = response.get("Items", [])

        # 2. Delete each item by primary key (message_id)
        for item in items:
            audit_table.delete_item(Key={"message_id": item["message_id"]})
        return True
    except Exception as e:
        logger.error(f"Error deleting from audit table: {e}")
        return False


def delete_filename_from_events_table(identifier) -> bool:

    # 1. Query the GSI to get all items with the given filename
    try:
        identifier_pk = f"{RAVS_URI}#{identifier}"
        response = events_table.query(
            IndexName="IdentifierGSI",
            KeyConditionExpression=Key("IdentifierPK").eq(identifier_pk)
        )
        items = response.get("Items", [])

        # 2. Delete each item by primary key (PK)
        for item in items:
            events_table.delete_item(Key={"PK": item["PK"]})
        return True
    except Exception as e:
        logger.warning(f"Error deleting from events table: {e}")
        return False


def poll_s3_file_pattern(prefix, search_pattern):
    """Poll the ACK_BUCKET for an ack file that contains the input_file_name as a substring."""

    response = s3_client.list_objects_v2(Bucket=ACK_BUCKET, Prefix=prefix)
    if "Contents" in response:
        for obj in response["Contents"]:
            key = obj["Key"]
            if search_pattern in key:
                return key
    return None
