import random
import string
from typing import Optional, Union

def get_text(text_str: str) -> Optional[Union[str, int]]:
    match text_str:
        case "missing":
            return None
        case "empty":
            return ""
        case "number":
            return random.randint(0, 9)
        case "gender_code":
            return "1"
        case "random_text":
            return "random"
        case "white_space":
            return " "
        case "white_space_array":
            return '[ " " ]'
        case _ if text_str.startswith("name_length_"):
            try:
                length = int(text_str.split("_")[2])
                return generate_random_length_name(length)
            except (IndexError, ValueError):
                raise ValueError(f"Invalid format for name_length: '{text_str}'")
        case _:
            raise ValueError(f"Unknown text type: '{text_str}'")

def generate_random_length_name(length=20) -> str:
    name = ''.join(random.choices(string.ascii_letters, k=length))
    return name.capitalize()

