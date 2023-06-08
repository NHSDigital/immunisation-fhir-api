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

def concatenate_params(**kwargs) -> str:
    output=''
    for p in kwargs.items():
        output += f'{p[0]}={p[1]}&'
    return output.rstrip('&')
