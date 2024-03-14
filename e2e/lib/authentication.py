import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from time import time
from urllib.parse import urlparse, parse_qs

import jwt
import requests
from lxml import html


@dataclass
class AuthenticationError(RuntimeError):
    message: str


class AuthType(str, Enum):
    APP_RESTRICTED = "ApplicationRestricted"
    NHS_LOGIN = "NhsLogin"
    CIS2 = "Cis2"


class BaseAuthentication(ABC):
    """interface for Apigee app authentication. ApigeeService uses this to get access token"""

    @abstractmethod
    def get_access_token(self):
        pass


@dataclass
class AppRestrictedCredentials:
    client_id: str
    kid: str
    private_key_content: str
    expiry_seconds: int = 30


@dataclass
class UserRestrictedCredentials:
    client_id: str
    client_secret: str
    callback_url: str = "https://oauth.pstmn.io/v1/callback"


@dataclass
class LoginUser:
    username: str
    password: str = ""


class AppRestrictedAuthentication(BaseAuthentication):
    def __init__(self, auth_url: str, config: AppRestrictedCredentials):
        self.expiry = config.expiry_seconds
        self.private_key = config.private_key_content
        self.client_id = config.client_id
        self.kid = config.kid
        self.token_url = f"{auth_url}/token"

    def __str__(self):
        return AuthType.APP_RESTRICTED.value

    def get_access_token(self):
        now = int(time())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_url,
            "iat": now,
            "exp": now + self.expiry,
            "jti": str(uuid.uuid4())
        }
        _jwt = jwt.encode(claims, self.private_key, algorithm='RS512', headers={"kid": self.kid})

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': _jwt
        }
        token_response = requests.post(self.token_url, data=data, headers=headers)

        if token_response.status_code != 200:
            raise AuthenticationError(f"ApplicationRestricted token POST request failed\n{token_response.text}")

        return token_response.json().get('access_token')


class AuthCodeFlow:
    def __init__(self, base_auth_url, app_credentials: UserRestrictedCredentials) -> None:
        self.app_creds = app_credentials
        self.auth_url = f"{base_auth_url}/authorize"
        self.token_url = f"{base_auth_url}/token"

    @staticmethod
    def extract_code(response) -> str:
        qs = urlparse(response.history[-1].headers["Location"]).query
        auth_code = parse_qs(qs)["code"]
        if isinstance(auth_code, list):
            # in case there's multiple, this was a bug at one stage
            auth_code = auth_code[0]

        return auth_code

    def get_access_token(self, scope: str, user_cred: LoginUser) -> str:
        login_session = requests.session()

        client_id = self.app_creds.client_id
        client_secret = self.app_creds.client_secret
        callback_url = self.app_creds.callback_url
        username = user_cred.username

        # Step1: login page
        authorize_resp = login_session.get(
            self.auth_url,
            params={
                "client_id": client_id,
                "redirect_uri": callback_url,
                "response_type": "code",
                "scope": scope,
                "state": str(uuid.uuid4()),
            },
        )
        assert authorize_resp.status_code == 200, authorize_resp.text

        # Step2: Submit the login form
        tree = html.fromstring(authorize_resp.content.decode())
        auth_form = tree.forms[0]

        form_url = auth_form.action
        form_data = {"username": username}

        code_resp = login_session.post(url=form_url, data=form_data)
        assert code_resp.status_code == 200, code_resp.text

        # Step3: extract code from redirect url
        auth_code = self.extract_code(code_resp)

        # Step4: Post the code to get access token
        token_resp = login_session.post(
            self.token_url,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": callback_url,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        assert token_resp.status_code == 200, token_resp.text

        return token_resp.json()["access_token"]


class Cis2Authentication(BaseAuthentication):
    def __init__(self, auth_url: str, config: UserRestrictedCredentials, default_user: LoginUser):
        self.code_flow = AuthCodeFlow(auth_url, config)
        self.user = default_user

    def __str__(self):
        return AuthType.CIS2.value

    def set_user(self, user: LoginUser):
        self.user = user

    def get_access_token(self) -> str:
        return self.code_flow.get_access_token("nhs-cis2", self.user)


class NHSLoginAuthentication(BaseAuthentication):
    def __init__(self, auth_url: str, config: UserRestrictedCredentials, default_user: LoginUser):
        self.code_flow = AuthCodeFlow(auth_url, config)
        self.user = default_user

    def __str__(self):
        return AuthType.NHS_LOGIN.value

    def set_user(self, user: LoginUser):
        self.user = user

    def get_access_token(self) -> str:
        return self.code_flow.get_access_token("nhs-login", self.user)
