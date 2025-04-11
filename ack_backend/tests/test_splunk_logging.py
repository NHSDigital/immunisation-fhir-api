"""Tests for ack lambda logging decorators"""

import unittest
from unittest.mock import patch, call
import json
from io import StringIO
from contextlib import ExitStack
from boto3 import client as boto3_client

class TestLoggingDecorators(unittest.TestCase):
    """Tests for the ack lambda logging decorators"""

    def setUp(self):
        print("Setting up test environment...")

    def run(self, result=None):
        print("Running test...")

if __name__ == "__main__":
    unittest.main()
