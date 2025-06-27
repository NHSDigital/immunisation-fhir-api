import os
import sys
from unittest.mock import patch

from tests.utils.mock_redis import MockRedisClient

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../src")

# TODO - probably shouldn't do this here. Mock in individual tests instead for clarity.
#  I tried setUpModule() but that wasn't called from __init__.py
redis_patcher = patch("clients.redis_client", MockRedisClient())
redis_patcher.start()
