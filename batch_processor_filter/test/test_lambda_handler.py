from unittest import TestCase

from lambda_handler import lambda_handler

class TestLambdaHandler(TestCase):
    def test_lambda_handler(self):
        result = lambda_handler({}, {})
        self.assertTrue(result)
