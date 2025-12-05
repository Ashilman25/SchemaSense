#signed cookies
#maybe switched to Redis or database backed sessions later

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

#secrets for signign session cookies
#change to load from .env later
SESSION_SECRET_KEY = "secret-key-to-add-to-env-later"
SESSION_COOKIE_NAME = "schemasense_session"
SESSION_MAX_AGE_DAYS = 365



def get_session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SESSION_SECRET_KEY)

def generate_session_id() -> str:
    random_part = secrets.token_hex(12) #24 chars
    return f"sess_{random_part}"



def serialize_session(session_id: str) -> str:
    serializer = get_session_serializer()
    return serializer.dumps(session_id)



def deserialize_session(signed_session: str, max_age_seconds: Optional[int] = None) -> Optional[str]:
    serializer = get_session_serializer()
    
    try:
        session_id = serializer.loads(
            signed_session,
            max_age = max_age_seconds
        )
        
        return session_id
    
    except (BadSignature, SignatureExpired):
        return None