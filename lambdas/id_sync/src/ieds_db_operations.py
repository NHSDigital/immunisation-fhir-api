from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name
from common.clients import get_delta_table

ieds_table = None


def get_ieds_table():
    """Get the IEDS table."""
    global ieds_table
    if ieds_table is None:
        ieds_tablename = get_ieds_table_name()
        ieds_table = get_delta_table(ieds_tablename)
    return ieds_table


def check_record_exist_in_IEDS(id: str) -> bool:
    """Check if a record exists in the IEDS table for the given ID."""
    search_patient_pk = f"Patient#{id}"

    # Only fetch 1 record to check existence
    response = get_ieds_table().query(
        KeyConditionExpression=Key("PK").eq(search_patient_pk),
        Limit=1
    )
    return response.get("Count", 0) > 0


def update_patient_id_in_IEDS(old_id: str, new_id: str) -> dict:
    """Update the patient ID in the IEDS table."""
    # check if old_id and new_id are not empty
    if not old_id or not new_id:
        return {"status": "error", "message": "Old ID and New ID cannot be empty"}
    else:
        # update the table with new id
        get_ieds_table().update_item(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )
        return {"status": "success", "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"}
