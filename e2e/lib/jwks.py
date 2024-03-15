import base64
import json
from dataclasses import dataclass

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass
class JwksData:
    private_key: str
    public_key: str
    key_id: str
    encoded_n: str = None

    def __init__(self, key_id: str, private_key_path: str = None, public_key_path: str = None):
        """it generates everything that is required for jwks. If you are not passing private/public key path then
        it will be generated dynamically"""

        self.key_id = key_id
        if private_key_path is None and public_key_path is None:
            self.private_key, self.public_key, self.encoded_n = _make_key_pair_n()
        else:
            with open(private_key_path, "r") as private_key:
                self.private_key = private_key.read()
            with open(public_key_path, "r") as public_key:
                self.public_key = public_key.read()

            pub_key = serialization.load_pem_public_key(self.public_key.encode(), backend=default_backend())
            n = pub_key.public_numbers().n
            n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
            self.encoded_n = base64.urlsafe_b64encode(n_bytes).decode('utf-8')

    def get_jwk(self):
        return {
            "kty": "RSA",
            "n": self.encoded_n,
            "e": "AQAB",
            "alg": "RS512",
            "kid": self.key_id}

    def get_jwks_url(self, base_url: str) -> str:
        jwks = json.dumps({"keys": [self.get_jwk()]})
        jwks_encoded = base64.urlsafe_b64encode(jwks.encode()).decode("utf-8")
        return f"{base_url}/{jwks_encoded}"


def _make_key_pair_n(key_size=4096) -> (str, str, str):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())

    prv = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())

    public_key = private_key.public_key()
    pub = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.PKCS1)

    n = public_key.public_numbers().n
    n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
    n_encoded = base64.urlsafe_b64encode(n_bytes).decode('utf-8')

    return prv.decode(), pub.decode(), n_encoded
