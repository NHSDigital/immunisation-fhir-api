from unittest import TestCase
from unittest.mock import Mock

from lambda_handler import lambda_handler


class TestLambdaHandler(TestCase):
    def test_lambda_handler_returns_true(self):
        lambda_handler({"Records": [{"eventID": "1234"}]}, Mock())
