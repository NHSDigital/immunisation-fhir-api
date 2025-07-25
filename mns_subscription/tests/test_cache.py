import json
import tempfile
import unittest

from cache import Cache


class TestCache(unittest.TestCase):
    def setUp(self):
        self.store = Cache(tempfile.gettempdir())

    def test_cache_put(self):
        """it should store cache in specified key"""
        value = {"foo": "a-foo", "bar": 42}
        key = "a_key"

        # When
        self.store.put(key, value)
        act_value = self.store.get(key)

        # Then
        self.assertDictEqual(value, act_value)

    def test_cache_put_overwrite(self):
        """it should store updated cache value"""
        value = {"foo": "a-foo", "bar": 42}
        key = "a_key"
        self.store.put(key, value)

        new_value = {"foo": "new-foo"}
        self.store.put(key, new_value)

        # When
        updated_value = self.store.get(key)

        # Then
        self.assertDictEqual(new_value, updated_value)

    def test_key_not_found(self):
        """it should return None if key doesn't exist"""
        value = self.store.get("it-does-not-exist")
        self.assertIsNone(value)

    def test_delete(self):
        """it should delete key"""
        key = "a_key"
        self.store.put(key, {"a": "b"})
        self.store.delete(key)

        value = self.store.get(key)
        self.assertIsNone(value)

    def test_write_to_file(self):
        """it should update the cache file"""
        value = {"foo": "a-long-foo-so-to-make-sure-truncate-is-working", "bar": 42}
        key = "a_key"
        self.store.put(key, value)
        # Add one and delete to make sure file gets updated
        self.store.put("to-delete-key", {"x": "y"})
        self.store.delete("to-delete-key")

        # When
        new_value = {"a": "b"}
        self.store.put(key, new_value)

        # Then
        with open(self.store.cache_file.name, "r") as stored:
            content = json.loads(stored.read())
            self.assertDictEqual(content[key], new_value)
