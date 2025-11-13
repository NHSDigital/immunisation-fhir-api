import json
from typing import Optional


class Cache:
    """Key-value file cache"""

    def __init__(self, directory):
        filename = f"{directory}/cache.json"
        with open(filename, "a+") as self.cache_file:
            self.cache_file.seek(0)
            content = self.cache_file.read()
        if len(content) == 0:
            self.cache_dict = {}
        else:
            self.cache_dict = json.loads(content)

    def put(self, key: str, value: dict):
        self.cache_dict[key] = value
        self._overwrite()

    def get(self, key: str) -> Optional[dict]:
        return self.cache_dict.get(key, None)

    def delete(self, key: str):
        if key not in self.cache_dict:
            return
        del self.cache_dict[key]

    def _overwrite(self):
        with open(self.cache_file.name, "w") as self.cache_file:
            self.cache_file.seek(0)
            self.cache_file.write(json.dumps(self.cache_dict))
            self.cache_file.truncate()
