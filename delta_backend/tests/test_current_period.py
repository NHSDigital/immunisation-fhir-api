import unittest
from datetime import datetime, timezone
from src.extractor import Extractor  # adjust this import to your actual path

class TestIsCurrentPeriod(unittest.TestCase):
    def setUp(self):
        self.extractor = Extractor(fhir_json_data={})
        self.occurrence = datetime(2025, 6, 12, 13, 0, 0, tzinfo=timezone.utc)

    def test_valid_period_in_range(self):
        name = {"period": {"start": "2025-06-01", "end": "2025-06-12"}}
        result = self.extractor._is_current_period(name, self.occurrence)
        self.assertTrue(result)

    def test_occurrence_after_end(self):
        name = {"period": {"start": "2025-06-01", "end": "2025-06-11"}}
        result = self.extractor._is_current_period(name, self.occurrence)
        self.assertFalse(result)

    def test_occurrence_before_start(self):
        name = {"period": {"start": "2025-06-13", "end": "2025-06-20"}}
        result = self.extractor._is_current_period(name, self.occurrence)
        self.assertFalse(result)

    def test_date_only_end(self):
        name = {"period": {"end": "2025-06-12"}}
        result = self.extractor._is_current_period(name, self.occurrence)
        self.assertTrue(result)  # because end-of-day logic applies

    def test_no_period(self):
        name = {}
        result = self.extractor._is_current_period(name, self.occurrence)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()