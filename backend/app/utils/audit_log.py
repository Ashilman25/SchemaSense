#secure logging

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from enum import Enum

audit_logger = logging.getLogger("schemasense.audit")

class AuditEventType(str, Enum):
    DB_PROVISION_SUCCESS = "db_provision_success"
    DB_PROVISION_FAILURE = "db_provision_failure"
    DB_DEPROVISION_SUCCESS = "db_deprovision_success"
    DB_DEPROVISION_FAILURE = "db_deprovision_failure"

    DATA_PREVIEW = "data_preview"
    DATA_INSERT = "data_insert"

    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    DB_CONFIG_CHANGED = "db_config_changed"

    SQL_VALIDATION_BLOCKED = "sql_validation_blocked"
    


class AuditEvent:
    
    def __init__(self, event_type: AuditEventType, session_id: Optional[str] = None, user_ip: Optional[str] = None, details: Optional[Dict[str, Any]] = None, success: bool = True, error_message: Optional[str] = None):
        self.timestamp = datetime.now(UTC).isoformat()
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
            
            
            
def log_db_provision_success(session_id: str, user_ip: str, db_name: str, mode: str, load_sample: bool) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DB_PROVISION_SUCCESS,
        session_id = session_id,
        user_ip = user_ip,
        details = {
            "db_name" : db_name,
            "mode" : mode,
            "load_sample" : load_sample
        },
        success = True
    )
    
    event.log(logging.INFO)
    
    
    

def log_db_provision_failure(session_id: str, user_ip: str, error: str, mode: Optional[str] = None) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DB_PROVISION_FAILURE,
        session_id = session_id,
        user_ip = user_ip,
        details = {"mode" : mode} if mode else {},
        success = False,
        error_message = error
    )
    
    event.log(logging.WARNING)




def log_db_deprovision_success(session_id: str, user_ip: str, db_name: str, db_id: int) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DB_DEPROVISION_SUCCESS,
        session_id = session_id,
        user_ip = user_ip,
        details = {
            "db_name" : db_name,
            "db_id" : db_id
        },
        success = True
    )
    
    event.log(logging.INFO)
    
    
    
def log_db_deprovision_failure(session_id: str, user_ip: str, db_name: Optional[str], error: str) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DB_DEPROVISION_FAILURE,
        session_id = session_id,
        user_ip = user_ip,
        details = {"db_name": db_name} if db_name else {},
        success = False,
        error_message = error
    )
    
    event.log(logging.WARNING)
    
    
    
    
def log_quota_exceeded(session_id: str, user_ip: str, quota_type: str, current_count: int, limit: int) -> None:
    event = AuditEvent(
        event_type = AuditEventType.QUOTA_EXCEEDED,
        session_id = session_id,
        user_ip = user_ip,
        details = {
            "quota_type": quota_type,
            "current_count": current_count,
            "limit": limit
        },
        success = False
    )
    
    event.log(logging.WARNING)
    
    
    
    
def log_rate_limit_exceeded(session_id: str, user_ip: str, endpoint: str, retry_after: int) -> None:
    event = AuditEvent(
        event_type = AuditEventType.RATE_LIMIT_EXCEEDED,
        session_id = session_id,
        user_ip = user_ip,
        details = {
            "endpoint": endpoint,
            "retry_after": retry_after
        },
        success = False
    )
    
    event.log(logging.WARNING)
    
    
    
def log_db_config_changed(session_id: str, user_ip: str, host: str, port: int, dbname: str) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DB_CONFIG_CHANGED,
        session_id = session_id,
        user_ip = user_ip,
        details = {
            "host" : host,
            "port" : port,
            "dbname" : dbname
        },
        success = True
    )
    
    event.log(logging.INFO)
    
    
    
def log_sql_validation_blocked(session_id: str, user_ip: str, reason: str, sql_snippet: Optional[str] = None) -> None:
    details = {"reason" : reason}

    if sql_snippet:
        details["sql_snippet"] = sql_snippet[:100] + ("..." if len(sql_snippet) > 100 else "")

    event = AuditEvent(
        event_type = AuditEventType.SQL_VALIDATION_BLOCKED,
        session_id = session_id,
        user_ip = user_ip,
        details = details,
        success = False
    )
    
    event.log(logging.WARNING)


def log_data_preview(session_id: str, user_ip: str, table: str, row_count: int, success: bool, error_message: Optional[str] = None) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DATA_PREVIEW,
        session_id = session_id,
        user_ip = user_ip,
        details = {"table": table, "rows": row_count},
        success = success,
        error_message = error_message,
    )
    level = logging.INFO if success else logging.WARNING
    event.log(level)


def log_data_insert(session_id: str, user_ip: str, table: str, row_count: int, success: bool, error_message: Optional[str] = None) -> None:
    event = AuditEvent(
        event_type = AuditEventType.DATA_INSERT,
        session_id = session_id,
        user_ip = user_ip,
        details = {"table": table, "rows": row_count},
        success = success,
        error_message =  error_message,
    )
    level = logging.INFO if success else logging.WARNING
    event.log(level)
