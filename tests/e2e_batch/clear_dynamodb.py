import boto3

# Get the DynamoDB table name
TABLE_NAME = "imms-internal-dev-imms-events"

if not TABLE_NAME:
    raise ValueError("DYNAMODB_TABLE_NAME environment variable is not set")

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def get_primary_keys():
    """Retrieve the primary key schema of the table."""
    response = table.key_schema
    return [key["AttributeName"] for key in response]


def get_total_count():
    """Get the total count of items in the table, handling pagination."""
    total_count = 0
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = table.scan(Select="COUNT", ExclusiveStartKey=last_evaluated_key)
        else:
            response = table.scan(Select="COUNT")

        total_count += response.get("Count", 0)
        last_evaluated_key = response.get("LastEvaluatedKey")

        if not last_evaluated_key:
            break

    return total_count


def clear_dynamodb():
    """Deletes all items from the DynamoDB table, handling pagination."""
    print(f"Clearing DynamoDB table: {TABLE_NAME}")

    primary_keys = get_primary_keys()
    if not primary_keys:
        raise ValueError("Unable to retrieve primary key schema")

    total_count = get_total_count()
    print(f"Total items before deletion: {total_count}")

    deleted_count = 0

    while True:
        scan = table.scan()
        items = scan.get("Items", [])

        if not items:
            break

        with table.batch_writer() as batch:
            for item in items:
                key = {pk: item[pk] for pk in primary_keys}
                batch.delete_item(Key=key)
                deleted_count += 1

        print(f"Deleted {len(items)} items...")

    print(f"Total {deleted_count} items deleted from DynamoDB")


if __name__ == "__main__":
    clear_dynamodb()
