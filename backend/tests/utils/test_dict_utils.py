import unittest

from utils import dict_utils


class TestDictUtils(unittest.TestCase):
    def test_get_field_returns_none_if_value_is_not_dict(self):
        """Test that the default None value is returned if the provided argument is not a dict"""
        result = dict_utils.get_field(["test"], "test_key")

        self.assertIsNone(result)

    def test_get_field_returns_default_value_if_key_not_in_dict(self):
        """Test that the default None value is returned if the given key is not present in the dict"""
        test_dict = {"test": "foo"}

        result = dict_utils.get_field(test_dict, "not_present")

        self.assertIsNone(result)

    def test_get_field_returns_value_from_nested_dict(self):
        """Test that a value is retrieved from a nested dictionary"""
        test_dict = {"a": {"b": {"c": 42}}}

        result = dict_utils.get_field(test_dict, "a", "b", "c")

        self.assertEqual(result, 42)

    def test_get_field_returns_a_dictionary_from_nested_dict(self):
        """Test that where the value to retrieve is a dictionary then this is also successful"""
        test_dict = {"a": {"b": {"c": {"foo": {"bar": "test"}}}}}

        result = dict_utils.get_field(test_dict, "a", "b", "c")

        self.assertDictEqual(result, {"foo": {"bar": "test"}})

    def test_get_field_returns_override_default_value_when_provided(self):
        """Test that when a key is not found and the user provides an override default value then this is returned"""
        test_dict = {"a": {"test": "testing"}}

        result = dict_utils.get_field(test_dict, "a", "does_not_exist", default="")

        self.assertEqual(result, "")
