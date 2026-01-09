import hmac
import os
import uuid
import datetime
from hashlib import sha256

def build_auth_header(mailbox_id: str, nonce: str = None, nonce_count: int = 0):
    mailbox_id = os.getenv("MAILBOX_ID")
    password = os.getenv("MAILBOX_PASSWORD")
    auth_schema_name = os.getenv("AUTH_SCHEMA_NAME")
    shared_key = os.getenv("SHARED_KEY")
    
    """ Generate MESH Authorization header for mailboxid. """
    # Generate a GUID if required.
    if not nonce:
        nonce = str(uuid.uuid4())
    # Current time formatted as yyyyMMddHHmm
    # for example, 4th May 2020 13:05 would be 202005041305
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")

    # for example, NHSMESH AMP01HC001:bd0e2bd5-218e-41d0-83a9-73fdec414803:0:202005041305
    hmac_msg = mailbox_id + ":" + nonce + ":" + str(nonce_count) + ":" + password + ":" + timestamp

    # HMAC is a standard crypto hash method built in the python standard library.
    hash_code = hmac.HMAC(shared_key.encode(), hmac_msg.encode(), sha256).hexdigest()
    return (
            auth_schema_name 
            + mailbox_id + ":"
            + nonce + ":"
            + str(nonce_count) + ":"
            + timestamp+ ":"
            + hash_code
    )

