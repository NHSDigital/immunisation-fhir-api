import base64
import urllib.parse
from constants import SEARCH_IMMUNIZATION_BY_IDENTIFIER_PARAMETERS, SEARCH_IMMUNIZATIONS_PARAMETERS


def body_to_dict(body):
    """
    Converts a body array of {'key': ..., 'value': ...} to a dict.
    """
    if isinstance(body, list):
        return {item['key']: item['value'] for item in body if 'key' in item and 'value' in item}
    return body if isinstance(body, dict) else {}


def check_route_parameters(query_params, body, valid_params: list, second_list: list = None):
    try:

        query_params = query_params or {}
        body_dict = body_to_dict(body)
        # merge query and body parameters
        all_params = {**query_params, **body_dict}

        found = False
        for param in all_params:
            if param in valid_params:
                found = True
                break
        
        for param in all_params:
            if param in valid_params or param in second_list:
                continue
            elif param == "id":
                continue
            else:
                raise ValueError(f"Invalid body parameter: {param}")
        return found
    except Exception as e:
        raise ValueError(f"Error checking route parameters: {e}")


def is_immunization_by_identifier(query_params, body):
    # check the parameters indicate search by identifier
    return check_route_parameters(query_params, body, SEARCH_IMMUNIZATION_BY_IDENTIFIER_PARAMETERS,
                                  SEARCH_IMMUNIZATIONS_PARAMETERS)

# def is_search_immunizations(query_params, body):
#     # check the parameters indicate search for immunizations
#     return check_route_parameters(query_params, body, SEARCH_IMMUNIZATIONS_PARAMETERS)

def get_parsed_body(body):
    if body:
        decoded_body = base64.b64decode(body).decode("utf-8")
        # Parse the URL encoded body
        return urllib.parse.parse_qs(decoded_body)
    return None