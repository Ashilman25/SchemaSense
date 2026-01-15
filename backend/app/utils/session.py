#signed cookies
#maybe switched to Redis or database backed sessions later

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings



def get_session_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret_key)

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
    
    
    
def get_or_create_session_id(request: Request, response: Response) -> str:
    settings = get_settings()
    session_cookie = request.cookies.get(settings.session_cookie_name)

    if session_cookie:
        max_age = settings.session_max_age_days * 24 * 60 * 60
        session_id = deserialize_session(session_cookie, max_age_seconds = max_age)

        if session_id:
            return session_id


    session_id = generate_session_id()
    signed_session = serialize_session(session_id)

    is_production = settings.environment.lower() in ("production", "prod", "demo")

    response.set_cookie(
        key = settings.session_cookie_name,
        value = signed_session,
        max_age = settings.session_max_age_days * 24 * 60 * 60,
        httponly = True,
        secure = is_production,
        samesite = "none" if is_production else "lax"  #none needed for cross origin cookies in prod
    )

    return session_id



def clear_session(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name)
    
    
    
    
#MAYBE FOR FUTURE
#JUST WANTED TO MAKE IT FOR NOW
class SessionStore:
    
    def __init__(self, db_connection):
        self.db = db_connection
        
    async def create_session(self, metadata: dict) -> str:
        raise NotImplementedError("Databased backed sessions not implemented yet")
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        raise NotImplementedError("Databased backed sessions not implemented yet")

    async def update_session(self, session_id: str, metadata: dict) -> None:
        raise NotImplementedError("Databased backed sessions not implemented yet")

    async def delete_session(self, session_id: str) -> None:
        raise NotImplementedError("Databased backed sessions not implemented yet")
