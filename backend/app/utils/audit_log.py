#secure logging

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

audit_logger = logging.getLogger("schemasense.audit")

class AuditEventType(str, Enum):
    DB_PROVISION_SUCCESS = "db_provision_success"
    DB_PROVISION_FAILURE = "db_provision_failure"
    DB_DEPROVISION_SUCCESS = "db_deprovision_success"
    DB_DEPROVISION_FAILURE = "db_deprovision_failure"

    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    DB_CONFIG_CHANGED = "db_config_changed"

    SQL_VALIDATION_BLOCKED = "sql_validation_blocked"
    


class AuditEvent:
    
    def __init__(self, event_type: AuditEventType, session_id: Optional[str] = None, user_ip: Optional[str] = None, details: Optional[Dict[str, Any]] = None, success: bool = True, error_message: Optional[str] = None):
        self.timestamp = datetime.utcnow().isoformat()
        self.event_type = event_type
        self.session_id = session_id or "anonymous"
        self.user_ip = user_ip or "unknown"
        self.details = details or {}
        self.success = success
        self.error_message = error_message
        
        
    def to_dict(self) -> Dict[str, Any]:
        event_dict = {
            "timestamp" : self.timestamp,
            "event_type" : self.event_type.value,
            "session_id" : self.session_id,
            "user_ip" : self.user_ip,
            "success" : self.success,
        }
        
        if self.details:
            event_dict["details"] = self.details
            
        if self.error_message:
            event_dict["error"] = self.error_message
            
        return event_dict
    
    def log(self, level: int = logging.INFO) -> None:
        audit_logger.log(level, f"AUDIT: {self.event_type.value}", extra = self.to_dict())
            