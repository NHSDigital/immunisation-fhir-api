from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name
from common.aws_dynamodb import get_dynamodb_table
from common.clients import logger, dynamodb_client
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
    logger.info(f"Check Id exists ID: {id}")
    items = get_items_from_patient_id(id, 1)

    if items or len(items) > 0:
        logger.info(f"Found patient ID: {id}")
        return True
    return False


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

        new_patient_pk = f"Patient#{new_id}"

        logger.info("Getting items to update in IEDS table...")
        items_to_update = get_items_from_patient_id(old_id)

        if not items_to_update:
            logger.warning(f"No items found to update for patient ID: {old_id}")
            return {
                "status": "success",
                "message": f"No items found to update for patient ID: {old_id}"
            }

        transact_items = []

        logger.info(f"Items to update: {len(items_to_update)}")
        ieds_table_name = get_ieds_table_name()
        for item in items_to_update:
            transact_items.append({
                'Update': {
                    'TableName': ieds_table_name,
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

            response = dynamodb_client.transact_write_items(TransactItems=batch)
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
        logger.info("Error details: %s", e)
        raise IdSyncException(
            message=f"Error updating patient Id from :{old_id} to {new_id}",
            nhs_numbers=[old_id, new_id],
            exception=e
        )


def get_items_from_patient_id(id: str, limit=BATCH_SIZE) -> list:
    """Get all items for patient ID."""
    logger.info(f"Getting items for patient id: {id}")
    patient_pk = f"Patient#{id}"
    try:
        response = get_ieds_table().query(
            IndexName='PatientGSI',  # query the GSI
            KeyConditionExpression=Key('PatientPK').eq(patient_pk),
            Limit=limit
        )

        if 'Items' not in response or not response['Items']:
            logger.warning(f"No items found for patient PK: {patient_pk}")
            return []

        return response['Items']
    except Exception as e:
        logger.exception(f"Error querying items for patient PK: {patient_pk}")
        raise IdSyncException(
            message=f"Error querying items for patient PK: {patient_pk}",
            nhs_numbers=[patient_pk],
            exception=e
        )
