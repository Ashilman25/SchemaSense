"""
Database provisioning endpoints for SchemaSense-managed Postgres.

Provides endpoints to:
- Provision new managed databases (shared cluster approach)
- Deprovision databases (admin/cleanup)
"""

import logging
import psycopg2
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db_provisioner import provision_database, DatabaseConfig
from app.db import set_database_config
from app.utils.session import get_or_create_session_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/db", tags=["provisioning"])


class ProvisionRequest(BaseModel):
    """Request body for database provisioning."""
    mode: Optional[str] = Field(default=None, description="Provisioning mode: 'managed' or 'ephemeral'")
    loadSampleData: bool = Field(default=False, description="Whether to load sample sales data")


class ProvisionResponse(BaseModel):
    """Response for successful database provisioning."""
    success: bool
    mode: str
    connection: DatabaseConfig


class ProvisionErrorResponse(BaseModel):
    """Response for failed database provisioning."""
    success: bool = False
    error: str
    message: str


class DeprovisionRequest(BaseModel):
    """Request body for database deprovisioning."""
    db_name: Optional[str] = None
    id: Optional[int] = None


def _check_quotas(session_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if provisioning is allowed based on per-session and global quotas.

    Args:
        session_id: Session identifier to check

    Returns:
        Tuple of (is_allowed, error_message)
    """
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn

    conn = None
    try:
        conn = psycopg2.connect(admin_dsn)

        with conn.cursor() as cur:
            # Check per-session quota
            cur.execute(
                """
                SELECT COUNT(*) FROM provisioned_dbs
                WHERE session_id = %s AND status = 'active'
                """,
                (session_id,)
            )
            session_count = cur.fetchone()[0]

            if session_count >= settings.provision_max_dbs_per_session:
                return False, f"Session quota exceeded. Maximum {settings.provision_max_dbs_per_session} databases per session."

            # Check global quota
            cur.execute(
                """
                SELECT COUNT(*) FROM provisioned_dbs
                WHERE status = 'active'
                """
            )
            global_count = cur.fetchone()[0]

            if global_count >= settings.provision_global_max_dbs:
                return False, f"Global quota exceeded. Please try again later."

        return True, None

    except Exception as e:
        logger.error(f"Quota check failed: {str(e)}")
        # On quota check failure, allow provisioning but log the error
        return True, None

    finally:
        if conn:
            conn.close()


def _verify_connectivity(db_config: DatabaseConfig) -> bool:
    """
    Verify that we can connect to the newly provisioned database.

    Args:
        db_config: Database configuration to test

    Returns:
        True if connection successful, False otherwise
    """
    from urllib.parse import quote_plus

    # URL-encode password to handle special characters
    encoded_password = quote_plus(db_config.password)
    dsn = f"postgresql://{db_config.user}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.dbname}"

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            return result[0] == 1
    except Exception as e:
        logger.error(f"Connectivity verification failed: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()


@router.post("/provision")
async def provision_db(
    request: Request,
    response: Response,
    body: ProvisionRequest
):
    """
    Provision a new SchemaSense-managed Postgres database.

    This endpoint:
    1. Derives session_id from the request cookie
    2. Checks per-session and global quotas
    3. Provisions a new database + role in the managed cluster
    4. Optionally loads sample sales data
    5. Verifies connectivity
    6. Stores the DatabaseConfig as the current connection for this session
    7. Returns connection details

    Request body:
        {
            "mode": "managed",          // optional, defaults to config setting
            "loadSampleData": false     // optional, defaults to false
        }

    Success response:
        {
            "success": true,
            "mode": "managed",
            "connection": {
                "host": "...",
                "port": 5432,
                "dbname": "schemasense_user_7f3a9c",
                "user": "schemasense_u_7f3a9c",
                "password": "<password>"
            }
        }

    Error responses:
        - quota_exceeded: User or global quota reached
        - provision_failed: Database provisioning failed
    """
    settings = get_settings()

    # Get or create session ID
    session_id = get_or_create_session_id(request, response)
    logger.info(f"Provision request from session: {session_id}")

    # Determine mode
    mode = body.mode or settings.provision_mode_default

    # Check quotas
    quota_ok, quota_error = _check_quotas(session_id)
    if not quota_ok:
        logger.warning(f"Quota exceeded for session {session_id}: {quota_error}")
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": "quota_exceeded",
                "message": quota_error
            }
        )

    # Provision the database
    try:
        db_config = provision_database(
            mode=mode,
            session_id=session_id,
            load_sample=body.loadSampleData
        )

        logger.info(f"Database provisioned successfully: {db_config.dbname}")

        # Verify connectivity
        if not _verify_connectivity(db_config):
            logger.error(f"Connectivity verification failed for {db_config.dbname}")
            raise Exception("Database created but connectivity verification failed")

        # Store as current connection for this session
        set_database_config(db_config)
        logger.info(f"Database config set for session: {session_id}")

        return {
            "success": True,
            "mode": mode,
            "connection": db_config.dict()
        }

    except NotImplementedError as e:
        logger.error(f"Unsupported provisioning mode: {mode}")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "unsupported_mode",
                "message": str(e)
            }
        )

    except Exception as e:
        logger.error(f"Provisioning failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "provision_failed",
                "message": f"Failed to provision database: {str(e)}"
            }
        )


@router.post("/deprovision")
async def deprovision_db(body: DeprovisionRequest):
    """
    Deprovision a managed database (admin/cleanup endpoint).

    This endpoint is NOT exposed in the UI for MVP.
    Used for:
    - Manual cleanup by administrators
    - TTL-based expiration jobs
    - Future admin tools

    Request body:
        {
            "db_name": "schemasense_user_abc123"  // OR
            "id": 42                               // internal provisioned_dbs.id
        }

    Success response:
        {
            "success": true,
            "message": "Database deprovisioned successfully"
        }
    """
    settings = get_settings()

    if not body.db_name and not body.id:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "missing_identifier",
                "message": "Either db_name or id must be provided"
            }
        )

    admin_dsn = settings.managed_pg_admin_dsn
    conn = None

    try:
        conn = psycopg2.connect(admin_dsn)
        conn.autocommit = True

        # Look up the database details
        with conn.cursor() as cur:
            if body.db_name:
                cur.execute(
                    """
                    SELECT id, db_name, db_role, status
                    FROM provisioned_dbs
                    WHERE db_name = %s
                    """,
                    (body.db_name,)
                )
            else:
                cur.execute(
                    """
                    SELECT id, db_name, db_role, status
                    FROM provisioned_dbs
                    WHERE id = %s
                    """,
                    (body.id,)
                )

            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": "not_found",
                        "message": "Database not found in provisioned_dbs"
                    }
                )

            db_id, db_name, db_role, status = row

            if status == "deleted":
                return {
                    "success": True,
                    "message": f"Database {db_name} already marked as deleted"
                }

        # Drop the database and role
        with conn.cursor() as cur:
            logger.info(f"Dropping database: {db_name}")

            # Terminate active connections first
            cur.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (db_name,)
            )

            # Drop database
            cur.execute(f"DROP DATABASE IF EXISTS {db_name}")

            # Drop role
            cur.execute(f"DROP ROLE IF EXISTS {db_role}")

            logger.info(f"Dropped database {db_name} and role {db_role}")

        # Update metadata
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE provisioned_dbs
                SET status = 'deleted'
                WHERE id = %s
                """,
                (db_id,)
            )

        logger.info(f"Deprovisioned database: {db_name}")

        return {
            "success": True,
            "message": f"Database {db_name} deprovisioned successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Deprovisioning failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "deprovision_failed",
                "message": f"Failed to deprovision database: {str(e)}"
            }
        )

    finally:
        if conn:
            conn.close()
