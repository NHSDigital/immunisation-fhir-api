import json
import unittest

from not_found_handler import ALLOWED_METHODS, not_found


class TestNotFoundHandler(unittest.TestCase):
    """Tests for the not_found_handler functionality"""

    def test_method_not_allowed_unsupported_method(self):
        """Test that unsupported HTTP methods return 405 Method Not Allowed"""
        event = {"httpMethod": "PATCH"}

        response = not_found(event, None)

        self.assertEqual(response["statusCode"], 405)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertEqual(response["headers"]["Allow"], "GET, POST, DELETE, PUT")

        # Verify the response body structure
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["severity"], "error")
        self.assertEqual(body["issue"][0]["code"], "not-supported")
        self.assertEqual(body["issue"][0]["diagnostics"], "Method Not Allowed")

    def test_method_not_allowed_other_unsupported_method(self):
        """Test that other unsupported HTTP methods also return 405"""
        unsupported_methods = ["PUTT", "PATCH", "HEAD", "OPTIONS", "TRACE", "CONNECT"]

        for method in unsupported_methods:
            with self.subTest(method=method):
                event = {"httpMethod": method}
                response = not_found(event, None)

                self.assertEqual(response["statusCode"], 405)
                self.assertEqual(response["headers"]["Allow"], "GET, POST, DELETE, PUT")

    def test_not_found_allowed_method(self):
        """Test that allowed HTTP methods return 404 Not Found"""
        allowed_methods = ALLOWED_METHODS  # ["GET", "POST", "DELETE", "PUT"]

        for method in allowed_methods:
            with self.subTest(method=method):
                event = {"httpMethod": method}
                response = not_found(event, None)

                self.assertEqual(response["statusCode"], 404)
                self.assertEqual(response["headers"]["Content-Type"], "application/json")
                self.assertNotIn("Allow", response["headers"])  # No Allow header for 404

                # Verify the response body structure
                body = json.loads(response["body"])
                self.assertEqual(body["resourceType"], "OperationOutcome")
                self.assertEqual(body["issue"][0]["severity"], "error")
                self.assertEqual(body["issue"][0]["code"], "not-found")
                self.assertEqual(body["issue"][0]["diagnostics"], "The requested resource was not found.")

    def test_not_found_missing_http_method(self):
        """Test that missing httpMethod defaults to 405 Method Not Allowed"""
        event = {}

        response = not_found(event, None)

        self.assertEqual(response["statusCode"], 405)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertEqual(response["headers"]["Allow"], "GET, POST, DELETE, PUT")

    def test_not_found_none_http_method(self):
        """Test that None httpMethod defaults to 405 Method Not Allowed"""
        event = {"httpMethod": None}

        response = not_found(event, None)

        self.assertEqual(response["statusCode"], 405)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertEqual(response["headers"]["Allow"], "GET, POST, DELETE, PUT")

    def test_allowed_methods_constant(self):
        """Test that ALLOWED_METHODS contains the expected HTTP methods"""
        expected_methods = ["GET", "POST", "DELETE", "PUT"]
        self.assertEqual(ALLOWED_METHODS, expected_methods)


if __name__ == "__main__":
    unittest.main()
