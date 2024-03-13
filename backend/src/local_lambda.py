import json
from decimal import Decimal


def load_string(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_json(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f, parse_float=Decimal)

    return json_data


def load_sample_data_json(file_name: str) -> dict:
    return load_json(f"../tests/sample_data/{file_name}")
