from common.clients import dynamodb_client, logger


def get_delta_table(table_name):
    """
    Initialize the DynamoDB table resource with exception handling.
    """
    try:
        logger.info("Initializing table: %s", table_name)
        delta_table = dynamodb_client.Table(table_name)
    except Exception as e:
        logger.exception("Error initializing Delta Table")
        raise e
    return delta_table
