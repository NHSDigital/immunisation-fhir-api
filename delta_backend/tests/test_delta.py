import unittest
from unittest.mock import patch

from src.delta import handler  # Import after setting environment variables


class DeltaTestCase(unittest.TestCase):

    def setUp(self):
        # Common setup if needed
        self.context = {}

    def test_handler(self):
        # Arrange
        event = { "text": "hello world"}

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)
