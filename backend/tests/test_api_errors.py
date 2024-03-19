import unittest

from models.errors import Severity, Code, create_operation_outcome


class TestApiErrors(unittest.TestCase):
    def test_error_to_uk_core2(self):
        code = Code.not_found

        severity = Severity.error
        diag = "a-diagnostic"
        error_id = "a-id"

        error = create_operation_outcome(resource_id=error_id, severity=severity, code=code, diagnostics=diag)

        issue = error["issue"][0]
        self.assertEqual(error["id"], error_id)
        self.assertEqual(issue["code"], "not-found")
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["diagnostics"], diag)
