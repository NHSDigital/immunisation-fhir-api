import json

from constants import DYNAMO_DB_TYPE_DESCRIPTORS, ImmsData


def extract_sqs_imms_data(sqs_record: dict) -> ImmsData:
    """
    Extract immunisation data from SQS DynamoDB stream event.
    Args: sqs_record: SQS record containing DynamoDB stream data
    Returns: Dict with unwrapped values ready to use
    """
    body = json.loads(sqs_record.get("body", "{}"))
    new_image = body.get("dynamodb", {}).get("NewImage", {})

    # Get top-level fields
    imms_id = _unwrap_dynamodb_value(new_image.get("ImmsID", {}))
    supplier_system = _unwrap_dynamodb_value(new_image.get("SupplierSystem", {}))
    vaccine_type = _unwrap_dynamodb_value(new_image.get("VaccineType", {}))
    operation = _unwrap_dynamodb_value(new_image.get("Operation", {}))

    imms_map = new_image.get("Imms", {}).get("M", {})

    return {
        "imms_id": imms_id,
        "supplier_system": supplier_system,
        "vaccine_type": vaccine_type,
        "operation": operation,
        "nhs_number": _unwrap_dynamodb_value(imms_map.get("NHS_NUMBER", {})),
        "person_dob": _unwrap_dynamodb_value(imms_map.get("PERSON_DOB", {})),
        "date_and_time": _unwrap_dynamodb_value(imms_map.get("DATE_AND_TIME", {})),
        "site_code": _unwrap_dynamodb_value(imms_map.get("SITE_CODE", {})),
    }


def _unwrap_dynamodb_value(value) -> str:
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
