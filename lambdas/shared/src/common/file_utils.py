"""General file utils"""

import os


def get_file_key_without_ext(file_key: str) -> str:
    return os.path.splitext(file_key)[0]
