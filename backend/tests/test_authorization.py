import unittest
from typing import Set

from authorization import (
    Authorization,
    UnknownPermission,
    EndpointOperation as Operation,
    PERMISSIONS_HEADER,
    AUTHENTICATION_HEADER,
    authorize,
    Permission,
    AuthType)
from models.errors import UnauthorizedError


def _make_aws_event(auth_type: AuthType, permissions: Set[str]):
    header = ",".join(permissions)
    return {
        "headers": {
            PERMISSIONS_HEADER: header,
            AUTHENTICATION_HEADER: auth_type.value
        }
    }


def _full_access(exclude: Set[Permission] = None):
    return {*Permission}.difference(exclude)


class TestAuthorizeDecorator(unittest.TestCase):
    """This is a test for the decorator itself not the authorization logic.
    This decorator uses Authorize class internally and it has its own tests"""

    class StubController:
        @authorize(Operation.READ)
        def read_endpoint(self, aws_event: dict):
            _ = aws_event
            return True

    def test_decorator(self):
        controller = TestAuthorizeDecorator.StubController()

        aws_event = _make_aws_event(AuthType.APP_RESTRICTED, {Permission.READ})
        # When authorized
        is_called = controller.read_endpoint(aws_event)
        self.assertTrue(is_called)

        aws_event = _make_aws_event(AuthType.APP_RESTRICTED, _full_access(exclude={Permission.READ}))
        with self.assertRaises(UnauthorizedError):
            # When unauthorized
            is_called = controller.read_endpoint(aws_event)
            self.assertFalse(is_called)


class TestAuthorization(unittest.TestCase):
    """This class is for testing Authorization class before identifying the authentication type.
    Each AuthenticationType has its own test class"""

    def setUp(self):
        self.authorization = Authorization()

    def test_unknown_authorization(self):
        """it should raise UnknownPermission if auth type can't be determined"""
        aws_event = {
            "headers": {
                PERMISSIONS_HEADER: str(Permission.READ),
                AUTHENTICATION_HEADER: "unknown auth type"
            }
        }

        with self.assertRaises(UnknownPermission):
            self.authorization.authorize(Operation.READ, aws_event)


class TestApplicationRestrictedAuthorization(unittest.TestCase):
    def setUp(self):
        self.authorization = Authorization()

    def test_parse_permissions_header(self):
        """it should parse the content of permissions header"""
        # test for case-insensitive, trim and duplicated
        permissions = {"immunization:read", "immunization:read", "immunization:create\n", "\timmunization:UPDATE ",
                       "immunization:delete", "immunization:search"}
        aws_event = _make_aws_event(AuthType.APP_RESTRICTED, permissions)

        # Try each operation. It's a pass if we don't get any exceptions
        for op in [*Operation]:
            try:
                # When
                self.authorization.authorize(op, aws_event)
            except (UnauthorizedError, UnknownPermission):
                self.fail()

    def test_unknown_permission(self):
        permissions = {"immunization:create", "bad-permission"}
        aws_event = _make_aws_event(AuthType.APP_RESTRICTED, permissions)

        with self.assertRaises(UnknownPermission):
            # When
            self.authorization.authorize(Operation.CREATE, aws_event)

    def test_authorization(self):
        """it authorizes each request based on the operation"""
        # For each operation we need to test both authorized and unauthorized scenarios.
        #  The set of permissions to get unauthorized should be the complement of authorized
        operations = {
            Operation.READ: {Permission.READ},
            Operation.CREATE: {Permission.CREATE},
            Operation.UPDATE: {Permission.UPDATE, Permission.CREATE},
            Operation.DELETE: {Permission.DELETE},
            Operation.SEARCH: {Permission.SEARCH},
        }
        for op in operations:
            # Authorized:
            required_perms = operations[op]
            aws_event = _make_aws_event(AuthType.APP_RESTRICTED, required_perms)
            try:
                self.authorization.authorize(op, aws_event)
            except RuntimeError:
                self.fail(f"Authorization test failed for operation {op}")

            # Unauthorized:
            unauthorized_perms = _full_access(exclude=required_perms)
            aws_event = _make_aws_event(AuthType.APP_RESTRICTED, unauthorized_perms)
            with self.assertRaises(UnauthorizedError):
                self.authorization.authorize(op, aws_event)


# NOTE: Cis2 works exactly the same as ApplicationRestricted.
class TestCis2Authorization(unittest.TestCase):
    def setUp(self):
        self.authorization = Authorization()

    def test_parse_permissions_header(self):
        """it should parse the content of the permissions header"""
        # test for case-insensitive, trim and duplicated
        permissions = {"immunization:read", "immunization:read", "immunization:create\n", "\timmunization:UPDATE ",
                       "immunization:delete", "immunization:search"}
        aws_event = _make_aws_event(AuthType.CIS2, permissions)

        # Try each operation. It's a pass if we don't get any exceptions
        for op in [*Operation]:
            try:
                # When
                self.authorization.authorize(op, aws_event)
            except (UnauthorizedError, UnknownPermission):
                self.fail()

    def test_unknown_permission(self):
        permissions = {"immunization:create", "bad-permission"}
        aws_event = _make_aws_event(AuthType.CIS2, permissions)

        with self.assertRaises(UnknownPermission):
            # When
            self.authorization.authorize(Operation.CREATE, aws_event)

    def test_authorization(self):
        """it authorizes each request based on the operation"""
        # For each operation we need to test both authorized and unauthorized scenarios.
        #  The set of permissions to get unauthorized should be the complement of authorized
        operations = {
            Operation.READ: {Permission.READ},
            Operation.CREATE: {Permission.CREATE},
            Operation.UPDATE: {Permission.UPDATE, Permission.CREATE},
            Operation.DELETE: {Permission.DELETE},
            Operation.SEARCH: {Permission.SEARCH},
        }
        for op in operations:
            # Authorized:
            required_perms = operations[op]
            aws_event = _make_aws_event(AuthType.CIS2, required_perms)
            try:
                self.authorization.authorize(op, aws_event)
            except RuntimeError:
                self.fail(f"Authorization test failed for operation {op}")

            # Unauthorized:
            unauthorized_perms = _full_access(exclude=required_perms)
            aws_event = _make_aws_event(AuthType.CIS2, unauthorized_perms)
            with self.assertRaises(UnauthorizedError):
                self.authorization.authorize(op, aws_event)
