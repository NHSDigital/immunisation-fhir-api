from constants import DYNAMO_DB_TYPE_DESCRIPTORS

"""
Recursion to fetch deeply nested values from DynamoDB stream events.
Time complexity: O(n) where n is the total number of keys in the nested structure.
For typical SQS payloads (~50-100 keys per iteration), this is negligible.
Cleaner than hardcoded path references like data['body']['dynamodb']['NewImage']['Imms']['M']['NHS_NUMBER']['S'].
"""


def find_imms_value_in_stream(sqs_event_data: dict, target_key: str):
    """
    Recursively search for a key and unwrap DynamoDB type descriptors.
    Args:
        sqs_event_data: Nested dict from SQS DynamoDB stream event
        target_key: The key to find (e.g., 'NHS_NUMBER', 'ImmsID')
    Returns: Unwrapped value if found, None otherwise
    """
    if isinstance(sqs_event_data, dict):
        for key, value in sqs_event_data.items():
            if key == target_key:
                return _unwrap_dynamodb_value(value)
            result = find_imms_value_in_stream(value, target_key)
            if result is not None:
                return result
    return None


def _unwrap_dynamodb_value(value):
    """
    Unwrap DynamoDB type descriptor to get the actual value.
    DynamoDB types: S (String), N (Number), BOOL, M (Map), L (List), NULL
    """
    if not isinstance(value, dict):
        return value

    # DynamoDB type descriptors
    if "NULL" in value:
        return None

    # Check other DynamoDB types
    for key in DYNAMO_DB_TYPE_DESCRIPTORS:
        if key in value:
            return value[key]

    # Not a DynamoDB type, return as-is
    return value
