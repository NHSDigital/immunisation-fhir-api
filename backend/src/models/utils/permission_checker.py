from enum import StrEnum

class ApiOperationCode(StrEnum):
    CREATE = "c"
    READ = "r"
    UPDATE = "u"
    DELETE = "d"
    SEARCH = "s"

def _expand_permissions(permissions: list[str]) -> dict[str, list[ApiOperationCode]]:
    expanded_permissions = {}
    for permission in permissions:
        vaccine_type, operation_codes_str = permission.split(".", maxsplit=1)
        vaccine_type = vaccine_type.lower()
        operation_codes = [
            operation_code
            for operation_code in operation_codes_str.lower()
            if operation_code in list(ApiOperationCode)
        ]
        expanded_permissions[vaccine_type] = operation_codes
    return expanded_permissions

def validate_permissions(permissions: list[str], operation: ApiOperationCode, vaccine_types: list[str]):
    expanded_permissions = _expand_permissions(permissions)
    print(f"operation: {operation}, expanded_permissions: {expanded_permissions}, vaccine_types: {vaccine_types}")
    return all([
        operation in expanded_permissions.get(vaccine_type.lower(), [])
        for vaccine_type in vaccine_types
    ])