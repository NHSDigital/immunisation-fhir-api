"""Utility module for interacting with the AWS API Gateway event provided to controllers"""
from typing import Optional

from aws_lambda_typing.events import APIGatewayProxyEventV1

from controller.constants import SUPPLIER_SYSTEM_HEADER_NAME
from models.errors import UnauthorizedError
from utils import dict_utils


def get_path_parameter(event: APIGatewayProxyEventV1, param_name: str) -> str:
    return dict_utils.get_field(
        event["pathParameters"],
        param_name,
        default=""
    )


def get_supplier_system_header(event: APIGatewayProxyEventV1) -> str:
    """Retrieves the supplier system header from the API Gateway event"""
    supplier_system: Optional[str] = dict_utils.get_field(dict(event), "headers", SUPPLIER_SYSTEM_HEADER_NAME)

    if supplier_system is None:
        # SupplierSystem header must be provided for looking up permissions
        raise UnauthorizedError()

    return supplier_system
