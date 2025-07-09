import unittest
from authorization import (
    Authorization,
    UnknownPermission,
    AUTHENTICATION_HEADER,
    authorize,
    AuthType
)
from models.errors import UnauthorizedError


def _make_aws_event(auth_type: AuthType):
    return {
        "headers": {
            AUTHENTICATION_HEADER: auth_type.value
        }
    }


class TestAuthorizeDecorator(unittest.TestCase):
    """Test the decorator itself, not the authorization logic."""

    class StubController:
        @authorize()
        def read_endpoint(self, aws_event: dict):
            return True

    def test_decorator_authorized(self):
        controller = TestAuthorizeDecorator.StubController()
        aws_event = _make_aws_event(AuthType.APP_RESTRICTED)
        is_called = controller.read_endpoint(aws_event)
        self.assertTrue(is_called)

    def test_decorator_unauthorized(self):
        controller = TestAuthorizeDecorator.StubController()
        aws_event = {
            "headers": {
                AUTHENTICATION_HEADER: "InvalidType"
            }
        }
        with self.assertRaises(UnknownPermission):
            controller.read_endpoint(aws_event)


class TestAuthorization(unittest.TestCase):
    """Test Authorization class."""

    def setUp(self):
        self.authorization = Authorization()

    def test_valid_auth_types(self):
        for auth_type in [AuthType.APP_RESTRICTED, AuthType.CIS2, AuthType.NHS_LOGIN]:
            aws_event = _make_aws_event(auth_type)
            try:
                self.authorization.authorize(aws_event)
            except Exception as e:
                self.fail(f"Authorization failed for valid type {auth_type}: {e}")

    def test_unknown_authorization(self):
        aws_event = {
            "headers": {
                AUTHENTICATION_HEADER: "unknown auth type"
            }
        }
        with self.assertRaises(UnknownPermission):
            self.authorization.authorize(aws_event)


class TestApplicationRestrictedAuthorization(unittest.TestCase):
    def setUp(self):
        self.authorization = Authorization()

    def test_valid_app_restricted_auth(self):
        aws_event = _make_aws_event(AuthType.APP_RESTRICTED)
        try:
            self.authorization.authorize(aws_event)
        except Exception as e:
            self.fail(f"Authorization failed unexpectedly: {e}")

    def test_invalid_auth_type_raises_unknown_permission(self):
        aws_event = {
            "headers": {
                AUTHENTICATION_HEADER: "InvalidAuthType"
            }
        }
        with self.assertRaises(UnknownPermission):
            self.authorization.authorize(aws_event)


class TestCis2Authorization(unittest.TestCase):
    def setUp(self):
        self.authorization = Authorization()

    def test_valid_cis2_auth(self):
        aws_event = _make_aws_event(AuthType.CIS2)
        try:
            self.authorization.authorize(aws_event)
        except Exception as e:
            self.fail(f"Authorization failed unexpectedly: {e}")

    def test_invalid_auth_type_raises_unknown_permission(self):
        aws_event = {
            "headers": {
                AUTHENTICATION_HEADER: "InvalidAuthType"
            }
        }
        with self.assertRaises(UnknownPermission):
            self.authorization.authorize(aws_event)