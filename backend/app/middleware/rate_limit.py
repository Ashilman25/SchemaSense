#rate limiting for API endpoints

import time
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request, HTTPException

from app.utils.logging_utils import get_secure_logger
from app.utils import audit_log

logger = get_secure_logger(__name__)

#use IP + session_id
class RateLimiter:
    
    def __init__(self):
        self._requests: Dict[str, list[float]] = defaultdict(list)
        
    def _cleanup_old_requests(self, identifier: str, window_seconds: int) -> None:
        current_time = time.time()
        cutoff = current_time - window_seconds
        
        if identifier in self._requests:
            self._requests[identifier] = [ts for ts in self._requests[identifier] if ts > cutoff]
            
    
    def is_rate_limited(self, identifier: str, max_requests: int, window_seconds: int) -> Tuple[bool, Optional[int]]:
        self._cleanup_old_requests(identifier, window_seconds)
        
        request_count = len(self._requests[identifier])
        
        if request_count >= max_requests:
            oldest_request = min(self._requests[identifier])
            retry_after = int((oldest_request + window_seconds) - time.time()) + 1
            
            return True, max(retry_after, 1)
        
        return False, None
        
        
    def record_request(self, identifier: str) -> None:
        self._requests[identifier].append(time.time())
        
        
_rate_limiter = RateLimiter()

def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def check_provision_rate_limit(request: Request, session_id: str, max_requests_per_hour: int = 5) -> None:
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"provision:{session_id}:{client_ip}"
    
    rate_limiter = get_rate_limiter()
    
    #1 hour window rate limit
    is_limited, retry_after = rate_limiter.is_rate_limited(
        identifier = identifier,
        max_requests = max_requests_per_hour,
        window_seconds = 3600
    )
    
    if is_limited:
        logger.warning(
            "Provision rate limit exceeded",
            session_id = session_id,
            client_ip = client_ip,
            retry_after = retry_after
        )

        #rate limit violated
        audit_log.log_rate_limit_exceeded(
            session_id = session_id,
            user_ip = client_ip,
            endpoint = "/api/db/provision",
            retry_after = retry_after
        )

        raise HTTPException(
            status_code = 429,
            detail = {
                "success" : False,
                "error" : "rate_limit_exceeded",
                "message" : f"Too many provision requests. Please try again in {retry_after} seconds.",
                "retry_after" : retry_after
            },
            headers = {"Retry-After": str(retry_after)}
        )
        
    rate_limiter.record_request(identifier)
    logger.info("Provision rate limit check passed", session_id = session_id, client_ip = client_ip)