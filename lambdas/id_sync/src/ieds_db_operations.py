import json

from boto3.dynamodb.conditions import Key

from common.aws_dynamodb import get_dynamodb_table
from common.clients import dynamodb_client, logger
from exceptions.id_sync_exception import IdSyncException
from os_vars import get_ieds_table_name
from utils import make_status

ieds_table = None
BATCH_SIZE = 25  # DynamoDB TransactWriteItems max batch size


def get_ieds_table():
    """Get the IEDS table."""
    global ieds_table
    if ieds_table is None:
        ieds_tablename = get_ieds_table_name()
        ieds_table = get_dynamodb_table(ieds_tablename)
    return ieds_table


def ieds_update_patient_id(old_id: str, new_id: str, items_to_update: list) -> dict:
    """Update the patient ID (new NHS number) in the IEDS table."""
    if not items_to_update:
        logger.info("No items found to update for patient NHS Number")
        return make_status("No items found to update for patient ID")

    logger.info(f"Items to update: {len(items_to_update)}")

    try:
        # Build transact items and execute them in batches via helpers to keep
        # the top-level function easy to read and test.
        transact_items = build_transact_items(old_id, new_id, items_to_update)

        all_batches_successful, total_batches = execute_transaction_in_batches(transact_items)

        # Consolidated response handling
        logger.info(f"All batches complete. Total batches: {total_batches}, All successful: {all_batches_successful}")

        if all_batches_successful:
            return make_status(f"IEDS update. {len(items_to_update)} item(s) updated in {total_batches} batch(es).")
        else:
            return make_status(
                "Failed to update some batches for patient ID",
                status="error",
            )

    except Exception as e:
        logger.exception("Error updating patient ID")
        raise IdSyncException(
            message="Error updating patient ID",
        ) from e


def get_items_from_patient_id(id: str) -> list:
    """Public wrapper: build PatientPK and return all matching items.

    Delegates actual paging to the internal helper `_paginate_items_for_patient_pk`.
    Raises IdSyncException on error.
    """
    patient_pk = f"Patient#{id}"
    try:
        return paginate_items_for_patient_pk(patient_pk)
    except IdSyncException:
        raise
    except Exception:
        logger.exception("Error querying items for patient PK")
        raise IdSyncException(
            message="Error querying items for patient PK",
        )


def paginate_items_for_patient_pk(patient_pk: str) -> list:
    """Internal helper that pages through the PatientGSI and returns all items.

    Raises IdSyncException when the DynamoDB response is malformed.
    """
    all_items: list = []
    last_evaluated_key = None
    while True:
        query_args = {
            "IndexName": "PatientGSI",
            "KeyConditionExpression": Key("PatientPK").eq(patient_pk),
        }
        if last_evaluated_key:
            query_args["ExclusiveStartKey"] = last_evaluated_key

        response = get_ieds_table().query(**query_args)

        if "Items" not in response:
            # Unexpected DynamoDB response shape - surface as IdSyncException
            logger.exception("Unexpected DynamoDB response: missing 'Items'")
            raise IdSyncException(
                message="No Items in DynamoDB response",
            )

        items = response.get("Items", [])
        all_items.extend(items)

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    if not all_items:
        logger.info("No items found for patient PK in VEDS database")
        return []

    return all_items


def extract_patient_resource_from_item(item: dict) -> dict | None:
    """
    Extract a Patient resource from an IEDS database.
    """
    patient_resource = item.get("Resource", None)

    if isinstance(patient_resource, str):
        try:
            patient_resource_parsed = json.loads(patient_resource)
        except json.JSONDecodeError:
            logger.error("Failed to decode patient_resource JSON string")
            return None
        patient_resource = patient_resource_parsed

    if not isinstance(patient_resource, dict):
        return None

    contained = patient_resource.get("contained") or []
    for response in contained:
        if isinstance(response, dict) and response.get("resourceType") == "Patient":
            return response

    return None


def build_transact_items(old_id: str, new_id: str, items_to_update: list) -> list:
    """Construct the list of TransactItems for DynamoDB TransactWriteItems.

    Each item uses a conditional expression to ensure PatientPK hasn't changed
    since it was read.
    """
    transact_items = []
    ieds_table_name = get_ieds_table_name()
    new_patient_pk = f"Patient#{new_id}"

    for item in items_to_update:
        old_patient_pk = item.get("PatientPK", f"Patient#{old_id}")

        transact_items.append(
            {
                "Update": {
                    "TableName": ieds_table_name,
                    "Key": {
                        "PK": {"S": item["PK"]},
                    },
                    "UpdateExpression": "SET PatientPK = :new_val",
                    "ConditionExpression": "PatientPK = :expected_old",
                    "ExpressionAttributeValues": {
                        ":new_val": {"S": new_patient_pk},
                        ":expected_old": {"S": old_patient_pk},
                    },
                }
            }
        )

    return transact_items


def execute_transaction_in_batches(transact_items: list) -> tuple:
    """Execute transact write items in batches of BATCH_SIZE.

    Returns (all_batches_successful: bool, total_batches: int).
    """
    all_batches_successful = True
    total_batches = 0

    for i in range(0, len(transact_items), BATCH_SIZE):
        batch = transact_items[i : i + BATCH_SIZE]
        total_batches += 1
        logger.info(f"Transacting batch {total_batches} of size: {len(batch)}")

        response = dynamodb_client.transact_write_items(TransactItems=batch)
        logger.info("Batch update complete. Response: %s", response)

        # Check each batch response
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            all_batches_successful = False
            logger.error(f"Batch {total_batches} failed with status: {response['ResponseMetadata']['HTTPStatusCode']}")

    return all_batches_successful, total_batches
