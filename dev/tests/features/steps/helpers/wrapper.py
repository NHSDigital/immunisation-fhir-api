import json, os
from helpers.api_ops import api_ops as api

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
    'retrieve': endpoints.IMMUNISATION,
    'immunisation search': endpoints.IMMUNISATION_SEARCH,
    'immunization search': endpoints.IMMUNISATION_SEARCH,
    'search': endpoints.IMMUNISATION_SEARCH,
    'snomed': endpoints.SNOMED,
}

def get_endpoint(action: str, type: str) -> str:
    return endpoints.SNOMED if type.lower() == 'snomed' else endpoint_dict.get(action)

def get_expected_result_file(result_type: str) -> json:
    file_path = os.path.join(os.getcwd(), 'dev/tests/test-data', f'{result_type}.json')
    with open(os.path.join(file_path), 'r') as text_file:
        text_data = text_file.read()
    return text_data

def invoke_api(action_type, endpoint, headers, params, body):
    resp = None
    match action_type.lower():
        case 'get' | 'retrieve' | 'search':
            resp = api.api_get(endpoint=endpoint, header=headers, param=params)
        case 'delete':
            pass
            # resp = api.api_delete(endpoint=endpoint, header=headers, param=params)
    if resp == None:
        raise AssertionError(f'API call for {action_type} failed.')
    else:
        return resp
