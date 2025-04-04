#!/usr/bin/env python3
import os

import requests


def get_access_token():
    ci = os.environ["AZ_CI"]
    cs = os.environ["AZ_CS"]
    tn = os.environ["AZ_TN"]
    url = f"https://login.microsoftonline.com/{tn}/oauth2/v2.0/token"
    data = {
        "client_id": ci,
        "client_secret": cs,
        "grant_type": "client_credentials",
        "scope": "https://app.vssps.visualstudio.com/.default",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url=url, data=data, headers=headers)
    token = res.json()

    return token["access_token"]


print(get_access_token())
