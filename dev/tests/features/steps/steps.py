from behave import given, when, then
from helpers.wrapper import *
from helpers.comparison_ops import *

@given('I am testing the {env} environment')
def step_impl(context, env: str):
    context.base_url = base_url.LOCAL if env.lower()=='local' else base_url.REF

@when('I invoke the {action} endpoint for the Immunization api')
def step_impl(context, action: str):
    endpoint = f'{context.base_url}{get_endpoint(action=action, type="immunization")}'
    resp = invoke_api(action_type='get', endpoint=endpoint, headers=None, params=None, body=None)
    context.response_code=resp.status_code
    context.response_text=resp.text

@when('I {action} {type} records with the parameters {params}')
def step_impl(context, action: str, type: str, params: str):
    endpoint = f'{context.base_url}{get_endpoint(action=action, type=type)}'
    params=params.replace(' ','&').replace('&&','&').replace(',','&')
    resp = invoke_api(action_type=action, endpoint=endpoint, headers=None, params=params, body=None)
    context.response_code=resp.status_code
    context.response_text=resp.text

@then('The response status code should be {status_code}')
def step_impl(context, status_code: int):
    expected = int(status_code)
    actual = int(context.response_code)
    assert are_equal(expected=expected, actual=actual), f'Response code does not match.  Expected {expected}, but actual {actual}.  Response text: {context.response_text}'

@then('The response text should be {response_text}')
def step_impl(context, response_text: str):
    expected = '' if response_text.lower()=='empty' else response_text
    actual = context.response_text
    assert are_equal(expected=expected, actual=actual), f'Response text does not match.  Expected {expected}, but actual {actual}'

@then('The response json should match {response_file}')
def step_impl(context, response_file: str):
    expected = get_expected_result_file(result_type=response_file)
    actual = context.response_text
    assert compare_json(expected=expected, actual=actual), f'Response text does not match.  Expected {expected}, but actual {actual}'
