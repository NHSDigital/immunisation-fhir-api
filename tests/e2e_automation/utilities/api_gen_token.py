import os
from utilities.aws_token import refresh_sso_token, set_aws_session_token
from urllib.parse import parse_qs, urlparse
import requests
import uuid
from lxml import html
from datetime import datetime, timezone, timedelta


def extract_code(response):
    qs = urlparse(response.history[-1].headers["Location"]).query
    auth_code = parse_qs(qs)["code"]
    if isinstance(auth_code, list):
        auth_code = auth_code[0]
    return auth_code

def get_access_token(context):
    login_session = requests.session()
    client_id = context.auth_client_Id
    client_secret = context.auth_client_Secret
    callback_url = context.callback_url
    username = context.username
    auth_url = context.auth_url
    token_url = context.token_url
    scope = context.scope
    
    #Login Page
    authorize_resp = login_session.get(
        auth_url,
        params={
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": scope,
            "state": str(uuid.uuid4()),
        },
    )
    assert authorize_resp.status_code == 200, authorize_resp.text

    #Submit the login form
    tree = html.fromstring(authorize_resp.content.decode())
    auth_form = tree.forms[0]
    form_url = auth_form.action
    form_data = {"username": username}
    code_resp = login_session.post(url=form_url, data=form_data)
    assert code_resp.status_code == 200, code_resp.text

    # Step3: extract code from redirect url
    auth_code = extract_code(code_resp)

    # Step4: Post the code to get access token
    token_resp = login_session.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": callback_url,
            "client_id": client_id,
            "client_secret": client_secret
        },
    )
    assert token_resp.status_code == 200, token_resp.text

    current_time = datetime.now(timezone.utc)

    #return token_resp.json()["access_token"], token_resp.json()["expires_in"], current_time
    return token_resp.json()["access_token"]
    

def is_token_valid(token_expires_in_time, token_generated_time):
    if token_expires_in_time is None or token_generated_time is None:
        return False
    expiration_time = token_generated_time + timedelta(seconds=int(token_expires_in_time))
    return datetime.now(timezone.utc) < expiration_time


def get_tokens(context, supplier_name):    
    env_vars_map = {
        "auth_client_Secret" :f"{supplier_name}_client_Secret", 
        "auth_client_Id": f"{supplier_name}_client_Id", 
    }

    for attr, env_var in env_vars_map.items():
        setattr(context, attr, os.getenv(env_var))
    
    # if not is_token_valid(context.token_expires_in, context.token_gen_time):
    #     context.token, context.token_expires_in, context.token_gen_time = get_access_token(context) 
    
    context.token = get_access_token(context)   
      
        