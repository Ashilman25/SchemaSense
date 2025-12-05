#helpers for secure logging

import re
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

#makes it like postgresql://user:***@host:port/db for example
def redact_password_from_dsn(dsn: str) -> str:
    if not dsn or not isinstance(dsn, str):
        return str(dsn)
    
    pattern = r'(postgresql://[^:]+:)([^@]+)(@.+)'
    
    def replace_password(match):
        return f"{match.group(1)}***{match.group(3)}"
    
    return re.sub(pattern, replace_password, dsn)




#redact sensitive info in dicts
def redact_dict(data: Dict[str, Any], sensitive_keys: Optional[list[str]] = None) -> Dict[str, Any]:
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
            'apikey', 'auth', 'credential', 'credentials', 'dsn',
            'connection_string', 'private_key', 'session_secret_key'
        ]
        
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = '***'
            
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, sensitive_keys)
            
        elif isinstance(value, str) and value.startswith('postgresql://'):
            redacted[key] = redact_password_from_dsn(value)
            
        else:
            redacted[key] = value
            
    return redacted
        
        
        
#logging dsn with redaction
def safe_log_dsn(dsn: str, logger: logging.Logger, level: int = logging.INFO, prefix: str = "") -> None:
    redacted = redact_password_from_dsn(dsn)
    message = f"{prefix}{redacted}" if prefix else redacted
    logger.log(level, message)
    


def safe_log_dict(data: Dict[str, Any], logger: logging.Logger, level: int = logging.INFO, message: str = "", sensitive_keys: Optional[list[str]] = None) -> None:
    redacted = redact_dict(data, sensitive_keys)

    if message:
        logger.log(level, f"{message}: {redacted}")
    else:
        logger.log(level, redacted)
        
        
    