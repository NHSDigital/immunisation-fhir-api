import json, os

# CONSTANTS
class base_url:
    LOCAL='http://0.0.0.0:8888'
    REF=''

class endpoints:
    ROOT='/'
    HEALTH='/health'
    IMMUNISATION='/immunisation'


endpoint_dict = {
    'root': endpoints.ROOT,
    'health': endpoints.HEALTH,
    'immunisation': endpoints.IMMUNISATION
}

def get_endpoint(type: str = None) -> str:
    return endpoint_dict.get(type)

def get_expected_result_file(result_type: str) -> json:
    file_path = os.path.join(os.getcwd(), 'dev/tests/test-data', f'{result_type}.json')
    with open(os.path.join(file_path), 'r') as text_file:
        text_data = text_file.read()
    return text_data

def compare_json(expected: json, actual: json) -> bool:
    expected = json.dumps(expected, sort_keys=True)
    actual = json.dumps(actual, sort_keys=True)
    return expected==actual