'''
    record Processor
'''
# from common.clients import get_delta_table
from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name, get_delta_table_name
from common.clients import get_delta_table

ieds_tablename = get_ieds_table_name()
delta_tablename = get_delta_table_name()


def check_records_exist(dynamodb_table, id: str) -> bool:
    # dynamodb query to check that records exist for the given ID
    search_patient_pk = f"Patient#{id}"
    response = dynamodb_table.query(
        KeyConditionExpression=Key("PK").eq(search_patient_pk)
    )
    return response.get("Count", 0) > 0


def update_patient_id(old_id: str, new_id: str):

    # check if old_id and new_id are not empty
    if not old_id or not new_id:
        return {"status": "error", "message": "Old ID and New ID cannot be empty"}
    else:
        return {"status": "success", "message": f"Updated patient {old_id} to {new_id}", "TODO": "Implement logic"}
