from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Set

from models.errors import UnauthorizedError


AUTHENTICATION_HEADER = "AuthenticationType"


@dataclass
class UnknownPermission(RuntimeError):
    """Error when the parsed value can't be converted to Permissions enum."""


class AuthType(str, Enum):
    """This backend supports all three types of authentication.
    An Apigee App should specify AuthenticationType in its custom attribute.
    Each Apigee app can only have one type of authentication which is enforced by onboarding process.
    See: https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation"""
    APP_RESTRICTED = "ApplicationRestricted",
    NHS_LOGIN = "NhsLogin",
    CIS2 = "Cis2",


class Authorization:
    """ Authorize the call based on the endpoint and the authentication type.
    This class uses the passed headers from Apigee to decide the type of authentication (Application Restricted,
    NHS Login or CIS2). Then, based on the requested operation, it authorizes the call. Unauthorized call will raise
    Unauthorized exception. It raises UnknownPermission if there is a parse error from Apigee app. That means raising
    UnknownPermission is due to proxy bad configuration, and should result in 500. Any invalid value, either
    insufficient permissions or bad string, will result in UnauthorizedError if it comes from user.
    """
   
    def authorize(self, aws_event: dict):
        auth_type = self._parse_auth_type(aws_event["headers"])
        
        if auth_type not in {AuthType.APP_RESTRICTED, AuthType.CIS2, AuthType.NHS_LOGIN}:
            raise UnauthorizedError()

    @staticmethod
    def _parse_auth_type(headers) -> AuthType:
        try:
            auth_type = headers[AUTHENTICATION_HEADER]
            return AuthType(auth_type)
        except ValueError:
            # The value of authentication type comes from apigee regardless of auth type. That's why
            #  we raise UnknownPermission in case of an error and not UnauthorizedError
            raise UnknownPermission()

def authorize():
    def decorator(func):
        auth = Authorization()

        @wraps(func)
        def wrapper(controller_instance, a):
            auth.authorize(a)
            return func(controller_instance, a)

        return wrapper

    return decorator
