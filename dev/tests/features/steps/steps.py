from behave import given, when, then
from libs.api_ops import api_ops as api
from libs.wrapper import *

@given('I am testing the {env} environment')
def step_impl(context, env: str):
    context.base_url = base_url.LOCAL if env.lower()=='local' else base_url.REF

@when('I invoke the {type} endpoint for the Immunization api')
def step_impl(context, type: str):
    endpoint = f'{context.base_url}{get_endpoint(type=type)}'
    resp = api.api_get(endpoint=endpoint, header=None, param=None)
    context.response_code=resp.status_code
    context.response_text=resp.text

@when('I invoke the {type} endpoint with the parameters {nhs_number} and {to_date}')
def step_impl(context, type: str, nhs_number: str, to_date: str):
    endpoint = f'{context.base_url}{get_endpoint(type=type)}'
    resp = api.api_get(endpoint=endpoint, header=None, param=None)
    context.response_code=resp.status_code
    context.response_text=resp.text

@then('The response status code should be {status_code}')
def step_impl(context, status_code: int):
    expected = int(status_code)
    actual = int(context.response_code)
    assert expected == actual, f'Response code does not match.  Expected {expected}, but actual {actual}'

@then('The response text should be {response_text}')
def step_impl(context, response_text: str):
    expected = '' if response_text.lower()=='empty' else response_text
    actual = context.response_text
    assert expected == actual, f'Response text does not match.  Expected {expected}, but actual {actual}'

