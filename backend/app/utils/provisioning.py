import secrets
import string
import re

#identifiers
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


    
#extractors
def extract_shortid_from_db_name(db_name: str) -> str | None:
    pattern = r'^schemasense_user_([a-f0-9]{6})$'
    match = re.match(pattern, db_name)
    return match.group(1) if match else None


def extract_shortid_from_role_name(role_name: str) -> str | None:
    pattern = r'^schemasense_u_([a-f0-9]{6})$'
    match = re.match(pattern, role_name)
    return match.group(1) if match else None



#validators
def validate_db_name(db_name: str) -> bool:
    return extract_shortid_from_db_name(db_name) is not None

def validate_role_name(role_name: str) -> bool:
    return extract_shortid_from_role_name(role_name) is not None


#getters
def get_role_name_from_db_name(db_name: str) -> str | None:
    shortid = extract_shortid_from_db_name(db_name)
    return f"schemasense_u_{shortid}" if shortid else None

def get_db_name_from_role_name(role_name: str) -> str | None:
    shortid = extract_shortid_from_role_name(role_name)
    return f"schemasense_user_{shortid}" if shortid else None 