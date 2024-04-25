import unittest

from batch.report import ReportEntry, ReportEntryTransformer


class TestReportEntryTransformer(unittest.TestCase):
    def test_entry_transformer(self):
        """it should transform ReportEntry to string"""

        entry = ReportEntry(message="an-error")

        result = ReportEntryTransformer.transform_error(entry)

        expected_result = '{"message": "an-error"}'
        self.assertEqual(result, expected_result)
