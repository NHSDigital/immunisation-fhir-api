import base64
import sys

import oath


def compute_totp_code(key_base32: str) -> str:
    key_hex = base64.b32decode(key_base32).hex()
    return oath.totp(key_hex)


if __name__ == "__main__":
    print(compute_totp_code(sys.argv[1]))
