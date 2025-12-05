import secrets
import string
import re

#generates role identifier with given prefix
def generate_safe_identifier(prefix: str) -> str:
    shortid = secrets.token_hex(3)
    return f"{prefix}{shortid}"

def generate_db_name() -> str:
    return generate_safe_identifier('schemasense_user_')

def generate_role_name() -> str:
    return generate_safe_identifier('schemasense_u_')

def generate_strong_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


    