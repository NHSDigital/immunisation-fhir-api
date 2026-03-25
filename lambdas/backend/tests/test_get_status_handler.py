import unittest

from get_status_handler import get_status_handler


class GetStatusHandler(unittest.TestCase):
    def test_success_get_status_handler(self):
        event = {}
        context = None
        response = get_status_handler(event, context)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], "OK")
