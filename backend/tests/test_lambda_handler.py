import unittest
from not_found_handler import not_found  # Replace with your Lambda file path

"test"


class TestLambdaHandler(unittest.TestCase):
    def test_unsupported_method(self):
        """Tests the function with an unsupported method (PATCH)."""

        event = {"httpMethod": "PATCH"}

        response = not_found(event, None)

        self.assertEqual(response["statusCode"], 405)

        self.assertEqual(
            response["headers"]["Allow"], ", ".join(["GET", "POST", "DELETE", "PUT"])
        )  # Check Allow header


if __name__ == "__main__":

    unittest.main()
