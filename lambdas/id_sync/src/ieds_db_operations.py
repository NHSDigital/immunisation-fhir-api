from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name
from common.aws_dynamodb import get_dynamodb_table
from common.clients import logger
from exceptions.id_sync_exception import IdSyncException

ieds_table = None


def get_ieds_table():
    """Get the IEDS table."""
    global ieds_table
    if ieds_table is None:
        ieds_tablename = get_ieds_table_name()
        ieds_table = get_dynamodb_table(ieds_tablename)
    return ieds_table


def ieds_check_exist(id: str) -> bool:
    """Check if a record exists in the IEDS table for the given ID."""
    logger.info(f"ieds_check_exist. Get ID: {id}")
    search_patient_pk = f"Patient#{id}"

    response = get_ieds_table().query(
        IndexName='PatientGSI',
        KeyConditionExpression=Key('PatientPK').eq(search_patient_pk),
        Limit=1
    )

    items = response.get('Items', [])
    found = len(items) > 0
    logger.info(f"ieds_check_exist. Record found: {found} for ID: {id}")
    return found


BATCH_SIZE = 25


def ieds_update_patient_id(old_id: str, new_id: str) -> dict:
    """Update the patient ID in the IEDS table."""
    logger.info(f"ieds_update_patient_id. Update patient ID from {old_id} to {new_id}")
    if not old_id or not new_id or not old_id.strip() or not new_id.strip():
        return {"status": "error", "message": "Old ID and New ID cannot be empty"}

    if old_id == new_id:
        return {"status": "success", "message": f"No change in patient ID: {old_id}"}

    try:
        logger.info(f"Updating patient ID in IEDS from {old_id} to {new_id}")
        ieds_table = get_ieds_table()
        new_patient_pk = f"Patient#{new_id}"
        old_patient_pk = f"Patient#{old_id}"

        logger.info("Getting items to update in IEDS table...")
        items_to_update = get_items_to_update(old_patient_pk)

        if not items_to_update:
            logger.warning(f"No items found to update for patient ID: {old_id}")
            return {
                "status": "success",
                "message": f"No items found to update for patient ID: {old_id}"
            }

        transact_items = []

        logger.info("loop through items to update...")
        logger.info(f"Items to update: {len(items_to_update)}")
        for item in items_to_update:
            logger.info("Update item")
            logger.info(f"Updating item: {item['PatientPK']}")
            transact_items.append({
                'Update': {
                    'TableName': get_ieds_table_name(),
                    'Key': {
                        'PK': {'S': item['PK']},
                    },
                    'UpdateExpression': 'SET PatientPK = :new_val',
                    'ExpressionAttributeValues': {
                        ':new_val': {'S': new_patient_pk}
                    }
                }
            })

        logger.info("Transacting items in IEDS table...")
        # success tracking
        all_batches_successful = True
        total_batches = 0

        # Batch transact in chunks of BATCH_SIZE
        for i in range(0, len(transact_items), BATCH_SIZE):
            batch = transact_items[i:i+BATCH_SIZE]
            total_batches += 1
            logger.info(f"Transacting batch {total_batches} of size: {len(batch)}")

            response = ieds_table.transact_write_items(TransactItems=batch)
            logger.info("Batch update complete. Response: %s", response)

            # Check each batch response
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                all_batches_successful = False
                logger.error(
                    f"Batch {total_batches} failed with status: {response['ResponseMetadata']['HTTPStatusCode']}")

        # Consolidated response handling
        logger.info(
            f"All batches complete. Total batches: {total_batches}, All successful: {all_batches_successful}")

        if all_batches_successful:
            return {
                "status": "success",
                "message":
                    f"IEDS update, patient ID: {old_id}=>{new_id}. {len(items_to_update)} updated {total_batches}."
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to update some batches for patient ID: {old_id}"
            }

    except Exception as e:
        logger.exception("Error updating patient ID")
        raise IdSyncException(
            message=f"Error updating patient Id from :{old_id} to {new_id}",
            nhs_numbers=[old_id, new_id],
            exception=e
        )
    # ✅ Fix: Remove duplicate raise
    # raise e  # Remove this line

# def test_ieds_insert_patient(patient_id: str) -> dict:  # NOSONAR
#     """Test function for inserting patient ID."""
#     logger.info("insert to db...")
#     # write the patient id to table
#     res = '{"resourceType": "Immunization"}'
#     result = get_ieds_table().put_item(Item={
#                     "PK": f"Patient#{patient_id}",
#                     "PatientPK": f"Patient#{patient_id}",
#                     "PatientSK": f"Patient#{patient_id}",
#                     "Resource": res,
#                     "IdentifierPK": "https://www.ieds.england.nhs.uk/#a7e06f66-339f-4b81-b2f6-016b88bfc422",
#                     "Operation": "CREATE",
#                     "Version": "1",
#                     "SupplierSystem": "RAVS",
#                 })

#     logger.info(f"Test result: {result}")
#     return result


def get_items_to_update(old_patient_pk: str) -> list:
    """Get items that need to be updated in the IEDS table."""
    logger.info(f"Getting items to update for old patient PK: {old_patient_pk}")
    try:
        response = get_ieds_table().query(
            KeyConditionExpression=Key('PatientPK').eq(old_patient_pk),
            Limit=BATCH_SIZE
        )

        if 'Items' not in response or not response['Items']:
            logger.warning(f"No items found for old patient PK: {old_patient_pk}")
            return []

        return response['Items']
    except Exception as e:
        logger.exception(f"Error querying items for old patient PK: {old_patient_pk}")
        raise IdSyncException(
            message=f"Error querying items for old patient PK: {old_patient_pk}",
            nhs_numbers=[old_patient_pk],
            exception=e
        )
