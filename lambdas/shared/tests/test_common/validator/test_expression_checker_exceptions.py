import unittest

from common.validator.expression_checker import ExpressionChecker
from common.validator.record_error import ErrorReport


class DummyParser:
    def __init__(self, data=None, raise_on_get=False):
        self._data = data or {}
        self._raise = raise_on_get

    def get_key_value(self, field_name):
        if self._raise:
            raise RuntimeError("boom")
        return [self._data.get(field_name, "")]


class StubLookup:
    def __init__(self, raise_on_call=False):
        self.raise_on_call = raise_on_call

    def find_lookup(self, value):
        if self.raise_on_call:
            raise RuntimeError("boom")
        return ""  # force error path


class StubKeyData:
    def __init__(self, raise_on_call=False):
        self.raise_on_call = raise_on_call

    def findKey(self, key_source, field_value):
        if self.raise_on_call:
            raise RuntimeError("boom")
        return False  # force error path


class TestExpressionCheckerExceptions(unittest.TestCase):
    def make_checker(self, data=None, report=True, raise_on_get=False):
        return ExpressionChecker(DummyParser(data, raise_on_get), False, report)

    def test_regex_unexpected_true_false(self):
        # expression_rule None causes re.search to raise
        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("REGEX", None, "r", "abc", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("REGEX", None, "r", "abc", 1))

    def test_in_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("IN", "ab", "f", None, 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("IN", "ab", "f", None, 1))

    def test_length_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("LENGTH", "x", "s", "abcd", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("LENGTH", "x", "s", "abcd", 1))

    def test_float_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("FLOAT", None, "f", "abc", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("FLOAT", None, "f", "abc", 1))

    def test_uuid_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("UUID", None, "u", "not-a-uuid", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("UUID", None, "u", "not-a-uuid", 1))

    def test_maxobjects_unexpected_true_false(self):
        class NoLen:
            pass

        ec = self.make_checker(report=True)
        self.assertIsInstance(ec.validate_expression("MAXOBJECTS", "1", "m", NoLen(), 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        self.assertIsNone(ec2.validate_expression("MAXOBJECTS", "1", "m", NoLen(), 1))

    def test_onlyif_unexpected_true_false(self):
        ec = self.make_checker(report=True, raise_on_get=True)
        self.assertIsInstance(ec.validate_expression("ONLYIF", "loc|VAL", "f", "x", 1), ErrorReport)
        ec2 = self.make_checker(report=False, raise_on_get=True)
        self.assertIsNone(ec2.validate_expression("ONLYIF", "loc|VAL", "f", "x", 1))

    def test_lookup_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        ec.data_look_up = StubLookup(raise_on_call=True)
        self.assertIsInstance(ec.validate_expression("LOOKUP", None, "l", "x", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        ec2.data_look_up = StubLookup(raise_on_call=True)
        self.assertIsNone(ec2.validate_expression("LOOKUP", None, "l", "x", 1))

    def test_keycheck_unexpected_true_false(self):
        ec = self.make_checker(report=True)
        ec.key_data = StubKeyData(raise_on_call=True)
        self.assertIsInstance(ec.validate_expression("KEYCHECK", "Site", "k", "val", 1), ErrorReport)
        ec2 = self.make_checker(report=False)
        ec2.key_data = StubKeyData(raise_on_call=True)
        self.assertIsNone(ec2.validate_expression("KEYCHECK", "Site", "k", "val", 1))

    def test_date_alias_and_upper_lower_edges(self):
        ec = self.make_checker({"d": "2025-01-01"})
        self.assertIsNone(ec.validate_expression("DATE", None, "d", "2025-01-01", 1))
        # unexpected exceptions for .isupper/.islower/St/E
        ec2 = self.make_checker()
        self.assertIsInstance(ec2.validate_expression("UPPER", None, "u", None, 1), ErrorReport)
        self.assertIsInstance(ec2.validate_expression("LOWER", None, "l", None, 1), ErrorReport)
        self.assertIsInstance(ec2.validate_expression("STARTSWITH", "a", "s", None, 1), ErrorReport)
        self.assertIsInstance(ec2.validate_expression("ENDSWITH", "a", "e", None, 1), ErrorReport)

    def test_nrange_out_of_range(self):
        ec = self.make_checker()
        self.assertIsInstance(ec.validate_expression("NRANGE", "1,10", "n", "11", 1), ErrorReport)

    def test_postcode_valid_and_unexpected(self):
        ec = self.make_checker()
        self.assertIsNone(ec.validate_expression("POSTCODE", None, "p", "EC1A 1BB", 1))
        self.assertIsInstance(ec.validate_expression("POSTCODE", None, "p", None, 1), ErrorReport)

    def test_nhsnumber_valid_and_unexpected(self):
        ec = self.make_checker()
        self.assertIsNone(ec.validate_expression("NHSNUMBER", None, "n", "61234567890", 1))
        self.assertIsInstance(ec.validate_expression("NHSNUMBER", None, "n", None, 1), ErrorReport)

    def test_in_pass_fail(self):
        ec = self.make_checker()
        self.assertIsNone(ec.validate_expression("IN", "ab", "f", "zzabzz", 1))
        self.assertIsInstance(ec.validate_expression("IN", "ab", "f", "zz", 1), ErrorReport)


if __name__ == "__main__":
    unittest.main()
