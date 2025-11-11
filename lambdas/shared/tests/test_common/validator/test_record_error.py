import unittest

from common.validator.error_report.record_error import ErrorReport, RecordError


class TestRecordError(unittest.TestCase):
    def test_error_report_to_dict_summarise_false(self):
        er = ErrorReport(code=5, message="msg", row=1, field="f", details="d", summarise=False)
        d = er.to_dict()
        self.assertEqual(d["code"], 5)
        self.assertIn("row", d)
        self.assertIn("field", d)
        self.assertIn("details", d)

    def test_error_report_to_dict_summarise_true(self):
        er = ErrorReport(code=5, message="msg", row=1, field="f", details="d", summarise=True)
        d = er.to_dict()
        self.assertEqual(d, {"code": 5, "message": "msg"})

    def test_record_error_str_and_repr(self):
        rexc = RecordError(1, "m", "x")
        self.assertIn("1", str(rexc))
        self.assertIn("m", repr(rexc))


if __name__ == "__main__":
    unittest.main()
