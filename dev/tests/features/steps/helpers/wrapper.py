import json, os

# CONSTANTS
class base_url:
    LOCAL='http://0.0.0.0:8888'
    REF=''

class endpoints:
    ROOT='/'
    HEALTH='/health'
    IMMUNISATION='/immunisation'
    IMMUNISATION_SEARCH='/immunisation/search'
    SNOMED='/snomed'


endpoint_dict = {
    'root': endpoints.ROOT,
    'health': endpoints.HEALTH,
    'immunisation': endpoints.IMMUNISATION,
    'immunization': endpoints.IMMUNISATION,
    'immunisation search': endpoints.IMMUNISATION_SEARCH,
    'immunization search': endpoints.IMMUNISATION_SEARCH,
    'snomed': endpoints.SNOMED,
}

def get_endpoint(type: str = None) -> str:
    return endpoint_dict.get(type)

def get_expected_result_file(result_type: str) -> json:
    file_path = os.path.join(os.getcwd(), 'dev/tests/test-data', f'{result_type}.json')
    with open(os.path.join(file_path), 'r') as text_file:
        text_data = text_file.read()
    return text_data
