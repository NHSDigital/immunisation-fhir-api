"""
While there are tests to run the csv line against the validator,
these tests focuses on the csv line parser functionality.
Rows mean values and headers are keys
"""

import unittest

from test_common.validator.testing_utils.constants import CSV_HEADER
from test_common.validator.testing_utils.constants import CSV_VALUES
from test_common.validator.testing_utils.csv_utils import build_row

from common.validator.parsers.csv_line_parser import CSVLineParser


class TestCSVLineParser(unittest.TestCase):
    def test_parse_normal(self):
        csv_parsers = CSVLineParser()
        csv_rows = build_row(CSV_HEADER, CSV_VALUES)
        csv_parsers.parse_csv_line(csv_rows, CSV_HEADER)
        self.assertEqual(csv_parsers.csv_file_data, CSV_VALUES)
        self.assertEqual(csv_parsers.get_key_value("NHS_NUMBER"), ["9000000009"])

    def test_extra_values_ignored(self):
        """
        Ignore values that do not have a corresponding key
        """
        csv_parsers = CSVLineParser()
        csv_parsers.parse_csv_line("9000000009,Alex,Trent", "NHS_NUMBER,PERSON_FORENAME,PERSON_SURNAME")
        self.assertEqual(
            csv_parsers.csv_file_data,
            {"NHS_NUMBER": "9000000009", "PERSON_FORENAME": "Alex", "PERSON_SURNAME": "Trent"},
        )
        self.assertEqual(csv_parsers.get_key_value("PERSON_FORENAME"), ["Alex"])

    def test_fewer_values_than_keys(self):
        """
        Test that fewer values (rows) than keys (columns/headers)
        raises an error when accessing key without value
        """
        csv_parsers = CSVLineParser()
        csv_parsers.parse_csv_line("9000000009,Alex", "NHS_NUMBER,PERSON_FORENAME,PERSON_SURNAME")
        self.assertIn("NHS_NUMBER", csv_parsers.csv_file_data)
        self.assertIn("PERSON_FORENAME", csv_parsers.csv_file_data)
        self.assertNotIn("PERSON_SURNAME", csv_parsers.csv_file_data)
        with self.assertRaises(KeyError):
            _ = csv_parsers.get_key_value("PERSON_SURNAME")

    def test_get_missing_key_raises(self):
        """
        Test that accessing a non-existent key raises KeyError"""
        csv_parsers = CSVLineParser()
        csv_parsers.parse_csv_line("9000000009,Alex", "NHS_NUMBER,PERSON_FORENAME,PERSON_SURNAME")
        with self.assertRaises(KeyError):
            _ = csv_parsers.get_key_value("VACCINE_TYPE")


if __name__ == "__main__":
    unittest.main()
