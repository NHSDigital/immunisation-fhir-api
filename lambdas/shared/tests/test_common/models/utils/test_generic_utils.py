"""Generic utils for tests"""

import unittest
from datetime import date, datetime

from test_common.testing_utils.generic_utils import format_date_types


class TestFormatFutureDates(unittest.TestCase):
    def test_date_mode_formats_dates_and_datetimes(self):
        inputs = [date(2100, 1, 2), datetime(2100, 1, 3, 12, 0, 0)]
        expected = ["2100-01-02", "2100-01-03"]
        self.assertEqual(format_date_types(inputs, mode="date"), expected)

    def test_datetime_mode_formats_dates_and_datetimes(self):
        inputs = [date(2100, 1, 2), datetime(2100, 1, 3, 12, 0, 0)]
        expected = ["2100-01-02", "2100-01-03T12:00:00"]
        self.assertEqual(format_date_types(inputs, mode="datetime"), expected)

    def test_default_auto_mode_is_currently_unsupported(self):
        # Current implementation raises TypeError when mode is not 'date' or 'datetime'
        inputs = [date(2100, 1, 2)]
        with self.assertRaises(TypeError):
            format_date_types(inputs)  # default mode is 'auto'


if __name__ == "__main__":
    unittest.main()
