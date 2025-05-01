def get_op_outcome( status_code: int, status_desc: str, diagnostics: str = None, record: str = None, operation_type: str = None) -> dict:
    """
    Constructs the operation_outcome dictionary.

    Args:
        status_code (int): status code e.g., "200", "500"
        status_desc (str): Operation's outcome
        diagnostics (str, optional): Additional diagnostic information.
        record (str, optional): record identifier (e.g., imms_id).
        operation_type (str, optional): The type of operation performed.


    Returns:
        dict: The constructed operation_outcome dictionary.
    """
    outcome = { "statusCode": str(status_code), "statusDesc": status_desc}
    if diagnostics:
        outcome["diagnostics"] = diagnostics
    if record:
        outcome["record"] = record
    if operation_type:
        outcome["operation_type"] = operation_type
    return outcome
