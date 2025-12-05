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
        
        
    def record_request(self, identifier: str) -> None:
        self._requests[identifier].append(time.time())