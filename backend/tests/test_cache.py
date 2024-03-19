import json
import tempfile
import unittest

from cache import Cache


class TestCache(unittest.TestCase):
    def setUp(self):
        self.cache = Cache(tempfile.gettempdir())

    def test_cache_put(self):
        """it should store cache in specified key"""
        value = {"foo": "a-foo", "bar": 42}
        key = "a_key"

        # When
        self.cache.put(key, value)
        act_value = self.cache.get(key)

        # Then
        self.assertDictEqual(value, act_value)

    def test_cache_put_overwrite(self):
        """it should store updated cache value"""
        value = {"foo": "a-foo", "bar": 42}
        key = "a_key"
        self.cache.put(key, value)

        new_value = {"foo": "new-foo"}
        self.cache.put(key, new_value)

        # When
        updated_value = self.cache.get(key)

        # Then
        self.assertDictEqual(new_value, updated_value)

    def test_key_not_found(self):
        """it should return None if key doesn't exist"""
        value = self.cache.get("it-does-not-exist")
        self.assertIsNone(value)

    def test_delete(self):
        """it should delete key"""
        key = "a_key"
        self.cache.put(key, {"a": "b"})
        self.cache.delete(key)

        value = self.cache.get(key)
        self.assertIsNone(value)

    def test_write_to_file(self):
        """it should update the cache file"""
        value = {"foo": "a-long-foo-so-to-make-sure-truncate-is-working", "bar": 42}
        key = "a_key"
        self.cache.put(key, value)
        # Add one and delete to make sure file gets updated
        self.cache.put("to-delete-key", {"x": "y"})
        self.cache.delete("to-delete-key")

        # When
        new_value = {"a": "b"}
        self.cache.put(key, new_value)

        # Then
        with open(self.cache.cache_file.name, "r") as stored:
            content = json.loads(stored.read())
            self.assertDictEqual(content[key], new_value)
