import os
import boto3
import subprocess
from boto3.dynamodb.conditions import Attr

import logging
logging.basicConfig(filename='debugLog.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def set_aws_session_token():
    try:
        print("token started.......")
        # Create a session using your AWS credentials
        session = boto3.Session()

        # Get the credentials object
        credentials = session.get_credentials()
        
        # Refresh credentials if needed and retrieve the session token
        credentials = credentials.get_frozen_credentials()
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        session_token = credentials.token
        
        # Set credentials as environment variables for the current process
        os.environ["AWS_ACCESS_KEY_ID"] = access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
        os.environ["AWS_SESSION_TOKEN"] = session_token

        # Use os.system to call AWS CLI commands and set credentials
        os.system(f"aws configure set aws_access_key_id {access_key}")
        os.system(f"aws configure set aws_secret_access_key {secret_key}")
        os.system(f"aws configure set aws_session_token {session_token}")

    except Exception as e:
        print(f"Error setting AWS session token: {e}")
        

def refresh_sso_token(profile_name):
    try:
        subprocess.run(['aws', 'sso', 'login', '--profile', profile_name], check=True)
        print(f"SSO token refreshed for profile: {profile_name}")

        # After login, load credentials from the profile and set as env vars
        session = boto3.Session(profile_name=profile_name)
        credentials = session.get_credentials().get_frozen_credentials()
        os.environ["AWS_ACCESS_KEY_ID"] = credentials.access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = credentials.secret_key
        os.environ["AWS_SESSION_TOKEN"] = credentials.token
    except subprocess.CalledProcessError as e:
        print(f"Error refreshing SSO token: {e}")


