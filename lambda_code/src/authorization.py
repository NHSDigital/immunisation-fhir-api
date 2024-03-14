from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Set

from models.errors import UnauthorizedError

PERMISSIONS_HEADER = "Permissions"
AUTHENTICATION_HEADER = "AuthenticationType"


@dataclass
class UnknownPermission(RuntimeError):
    """Error when the parsed value can't be converted to Permissions enum."""


class EndpointOperation(Enum):
    """The kind of operation.
    This maps one-to-one to each endpoint. Authorization class decides whether there are sufficient permissions or not.
    The caller is responsible for passing the correct operation.
    """
    READ = 0,
    CREATE = 1,
    UPDATE = 2,
    DELETE = 3,
    SEARCH = 4,


class AuthType(str, Enum):
    """This backend supports all three types of authentication.
    An Apigee App should specify AuthenticationType in its custom attribute.
    Each Apigee app can only have one type of authentication which is enforced by onboarding process.
    See: https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation"""
    APP_RESTRICTED = "ApplicationRestricted",
    NHS_LOGIN = "NnsLogin",
    CIS2 = "Cis2",


class Permission(str, Enum):
    """Permission name for each operation that can be done to an Immunization Resource
    An Apigee App should specify a set of these as a comma-separated custom attribute.
    Permission works the same way as 'scope' but, in this case, they're called permission to distinguish them from
    OAuth2 scopes"""
    READ = "immunization:read"
    CREATE = "immunization:create"
    UPDATE = "immunization:update"
    DELETE = "immunization:delete"
    SEARCH = "immunization:search"


class Authorization:
    """ Authorize the call based on the endpoint and the authentication type.
    This class uses the passed headers from Apigee to decide the type of authentication (Application Restricted,
    NHS Login or CIS2). Then, based on the requested operation, it authorizes the call. Unauthorized call will raise
    Unauthorized exception. It raises UnknownPermission if there is a parse error from Apigee app. That means raising
    UnknownPermission is due to proxy bad configuration, and should result in 500. Any invalid value, either
    insufficient permissions or bad string, will result in UnauthorizedError if it comes from user.
    """

    def authorize(self, operation: EndpointOperation, aws_event: dict):
        auth_type = self._parse_auth_type(aws_event["headers"])
        if auth_type == AuthType.APP_RESTRICTED:
            self._app_restricted(operation, aws_event)
        if auth_type == AuthType.CIS2:
            self._cis2(operation, aws_event)
        if auth_type == AuthType.NHS_LOGIN:
            self._nhs_login(operation, aws_event)
        else:
            UnauthorizedError()

    _app_restricted_map = {
        EndpointOperation.READ: {Permission.READ},
        EndpointOperation.CREATE: {Permission.CREATE},
        EndpointOperation.UPDATE: {Permission.UPDATE, Permission.CREATE},
        EndpointOperation.DELETE: {Permission.DELETE},
        EndpointOperation.SEARCH: {Permission.SEARCH},
    }

    def _app_restricted(self, operation: EndpointOperation, aws_event: dict) -> None:
        allowed = self._parse_permissions(aws_event["headers"])
        requested = self._app_restricted_map[operation]
        if not requested.issubset(allowed):
            raise UnauthorizedError()

    def _cis2(self, operation: EndpointOperation, aws_event: dict) -> None:
        # Cis2 works exactly the same as ApplicationRestricted
        self._app_restricted(operation, aws_event)

    def _nhs_login(self, operation: EndpointOperation, aws_event: dict) -> None:
        # NHS Login works exactly the same as ApplicationRestricted
        self._app_restricted(operation, aws_event)

    @staticmethod
    def _parse_permissions(headers) -> Set[Permission]:
        """Given headers return a set of Permissions. Raises UnknownPermission"""

        content = headers.get(PERMISSIONS_HEADER, "")
        # comma-separate the Permissions header then trim and finally convert to lowercase
        parsed = [str.strip(str.lower(s)) for s in content.split(",")]

        permissions = set()
        for s in parsed:
            try:
                permissions.add(Permission(s))
            except ValueError:
                raise UnknownPermission()

        return permissions

    @staticmethod
    def _parse_auth_type(headers) -> AuthType:
        try:
            auth_type = headers[AUTHENTICATION_HEADER]
            return AuthType(auth_type)
        except ValueError:
            # The value of authentication type comes from apigee regardless of auth type. That's why
            #  we raise UnknownPermission in case of an error and not UnauthorizedError
            raise UnknownPermission()


def authorize(operation: EndpointOperation):
    def decorator(func):
        auth = Authorization()

        @wraps(func)
        def wrapper(controller_instance, a):
            auth.authorize(operation, a)
            return func(controller_instance, a)

        return wrapper

    return decorator
