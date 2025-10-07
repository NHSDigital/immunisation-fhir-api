from common.clients import dynamodb_resource, logger


def get_dynamodb_table(table_name):
    """
    Initialize the DynamoDB table resource with exception handling.
    """
    try:
        logger.info("Initializing table: %s", table_name)
        return dynamodb_resource.Table(table_name)
    except Exception as e:
        logger.exception("Error initializing DynamoDB table: %s", table_name)
        raise e
