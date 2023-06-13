import json

def are_equal(expected: object, actual: object) -> bool:
    return expected == actual

def is_string(actual: object) -> bool:
    return isinstance(actual, str)

def compare_json(expected: json, actual: json) -> bool:
    expected = json.dumps(expected, sort_keys=True)
    actual = json.dumps(actual, sort_keys=True)
    return expected==actual