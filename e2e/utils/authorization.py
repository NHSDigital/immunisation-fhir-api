from enum import Enum
from typing import Set


class Permission(str, Enum):
    READ = "immunization:read"
    CREATE = "immunization:create"
    UPDATE = "immunization:update"
    DELETE = "immunization:delete"
    SEARCH = "immunization:search"


def make_permissions_attribute(permissions: Set[Permission]) -> (str, str):
    """It generates an attribute value for an application restricted app. It returns key and value"""
    return "Permissions", ",".join(permissions)


def app_full_access(exclude: Set[Permission] = None) -> Set[Permission]:
    exclude = exclude if exclude else {}
    return {*Permission}.difference(exclude)
