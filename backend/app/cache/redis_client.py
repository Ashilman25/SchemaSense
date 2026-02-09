import redis
import json
from app.config import get_settings
from app.utils.logging_utils import get_secure_logger
from app.utils import audit_log

logger = get_secure_logger(__name__)

class RedisClient:
    def __init__(self):
        settings = get_settings()
        
        if not settings.redis_enabled:
            logger.warning("Redis is disabled in settings")
            self.client = None
            
        if not settings.redis_url:
            logger.warning("Redis URL is not configured")
            self.client = None
        
        if settings.redis_enabled and settings.redis_url:
            self.client = redis.from_url(settings.redis_url)
        
        
            
            
    def get_response(self, key: str) -> dict:
        if not self.client:
            return {"status" : 0}

        try:
            value = self.client.get(key)
            if value:
                data = {
                    "status" : 1,
                    "data" : json.loads(value)
                }
                return data
            
            else:
                return {"status" : 0}

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis unavailable in get_response", key = key, error = str(e))
            
        except json.JSONDecodeError as e:
            logger.warning("Corrupted cache value in get_response", key = key, error = str(e))

        return {"status" : 0}
    
    
    def set_response(self, key: str, value: dict, ttl_seconds: int = None) -> dict:
        if not self.client:
            return {"status" : 0}

        try:
            self.client.set(key, json.dumps(value), ex=ttl_seconds)
            return {"status" : 1}

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis unavailable in set_response", key = key, error = str(e))

        return {"status" : 0}
    
    
    def delete_key(self, key: str) -> dict:
        if not self.client:
            return {"status" : 0}

        try:
            self.client.delete(key)
            return {"status" : 1}

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis unavailable in delete_key", key = key, error = str(e))

        return {"status" : 0}
    
    def delete_pattern(self, pattern: str) -> dict:
        if not self.client:
            return {"status" : 0}

        try:
            for key in self.client.scan_iter(pattern):
                self.client.delete(key)

            return {"status" : 1}

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis unavailable in delete_pattern", pattern = pattern, error = str(e))

        return {"status" : 0}
    
    
    
    
    def health_check(self) -> bool:
        if not self.client:
            return False

        try:
            return self.client.ping()

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis health check failed", error = str(e))

        return False
    
    
    
_client = RedisClient()
def get_redis_client() -> RedisClient:
    return _client


    
