from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name
from common.aws_dynamodb import get_delta_table
from common.clients import logger

ieds_table = None


def get_ieds_table():
    """Get the IEDS table."""
    global ieds_table
    if ieds_table is None:
        ieds_tablename = get_ieds_table_name()
        ieds_table = get_delta_table(ieds_tablename)
    return ieds_table


def ieds_check_exist(id: str) -> bool:
    """Check if a record exists in the IEDS table for the given ID."""
    search_patient_pk = f"Patient#{id}"

    # Only fetch 1 record to check existence
    response = get_ieds_table().query(
        KeyConditionExpression=Key("PK").eq(search_patient_pk),
        Limit=1
    )
    return response.get("Count", 0) > 0


def ieds_update_patient_id(old_id: str, new_id: str) -> dict:
    """Update the patient ID in the IEDS table."""
    logger.info(f"ieds_update_patient_id. Update patient ID from {old_id} to {new_id}")
    if not old_id or not new_id or not old_id.strip() or not new_id.strip():
        return {"status": "error", "message": "Old ID and New ID cannot be empty"}

    if old_id == new_id:
        return {"status": "success", "message": f"No change in patient ID: {old_id}"}

    try:
        # Update the table with new id
        response = get_ieds_table().update_item(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

        # Check update successful
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {
                "status": "success",
                "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to update patient ID: {old_id}"
            }

    except Exception as e:
        logger.exception("Error updating patient ID")
        # Handle any exceptions that occur during the update
        raise e
