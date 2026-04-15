import unittest

from common.batch.eof_utils import is_eof_message, make_batch_eof_message


class TestEofUtils(unittest.TestCase):
    expected_eof_message = {
        "created_at_formatted_string": "2025-01-24T12:35:00Z",
        "file_key": "file_key.csv",
        "message": "EOF",
        "row_id": "id-123^500",
        "supplier": "TEST_SUPPLIER",
        "vax_type": "COVID",
    }

    def test_get_eof_utils_creates_valid_eof_message(self):
        self.assertDictEqual(
            make_batch_eof_message("file_key.csv", "TEST_SUPPLIER", "COVID", "2025-01-24T12:35:00Z", "id-123", 500),
            self.expected_eof_message,
        )

    def test_is_eof_message_returns_false_if_not_an_eof_message(self):
        mock_non_eof_message = {
            "created_at_formatted_string": "2025-01-24T12:35:00Z",
            "file_key": "file_key.csv",
            "row_id": "id-123^1003",
            "supplier": "TEST_SUPPLIER",
            "vax_type": "COVID",
        }

        self.assertFalse(is_eof_message(mock_non_eof_message))

    def test_is_eof_message_returns_true_when_message_is_an_eof_message(self):
        self.assertTrue(is_eof_message(self.expected_eof_message))
