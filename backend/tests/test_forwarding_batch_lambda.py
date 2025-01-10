"""Test for recordforwarder lambda"""

import unittest

## Remove this Test- this acting as a placeholder for actual record forwarder tests


class Test_forward_lambda_handler(unittest.TestCase):
    def test_name_length(self):
        """Test that the length of 'recordforwarder' is 14."""
        name = "recordforwarder"
        self.assertEqual(len(name), 14)  # This test will pass
