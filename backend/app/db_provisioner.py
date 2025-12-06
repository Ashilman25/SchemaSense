import psycopg2
from typing import Optional
from pathlib import Path
from pydantic import BaseModel

from app.config import get_settings
from app.utils.provisioning import generate_strong_password
from app.utils.logging_utils import get_secure_logger

logger = get_secure_logger(__name__)

class DatabaseConfig(BaseModel):
    host: str
    port: int
    dbname: str
    user: str
    password: str
    
    
def provision_database(mode: str, session_id: Optional[str] = None, load_sample: bool = False) -> DatabaseConfig:
    settings = get_settings()
    
    if mode == "managed":
        return _provision_managed_database(session_id, load_sample)
    
    elif mode == "ephemeral":
        raise NotImplementedError("maybe later")
    else:        
        raise ValueError(f"Invalid provisioning mode: {mode}. Expected 'managed'.")
    
    

#db in shared postgres cluster
def _provision_managed_database(session_id: Optional[str], load_sample: bool) -> DatabaseConfig:
    settings = get_settings()

    # Generate a single shortid and use it for both database and role names
    import secrets
    shortid = secrets.token_hex(3)  # 6 character hex string
    db_name = f"schemasense_user_{shortid}"
    role_name = f"schemasense_u_{shortid}"
    password = generate_strong_password()
    
    admin_dsn = settings.managed_pg_admin_dsn
    
    logger.info(f"Starting provisioning for session", session_id = session_id, db_name = db_name)
    
    admin_conn = None
    role_created = False
    db_created = False
    metadata_recorded = False
    
    try:
        admin_conn = psycopg2.connect(admin_dsn)
        admin_conn.autocommit = True #required for CREATE DATABASE
        
        with admin_conn.cursor() as cur:
            cur.execute(f"""
                        CREATE ROLE {role_name}
                        LOGIN
                        PASSWORD %s
                        NOSUPERUSER
                        NOCREATEDB
                        CREATEROLE
                        NOREPLICATION
                        CONNECTION LIMIT {settings.provision_connection_limit_per_role}
                        """, (password,))
            
            role_created = True
            logger.info("Created role", role_name = role_name)

            #role level timeouts
            cur.execute(f"ALTER ROLE {role_name} SET statement_timeout = {settings.provision_default_statement_timeout_ms}")
            cur.execute(f"ALTER ROLE {role_name} SET idle_in_transaction_session_timeout = {settings.provision_idle_in_transaction_timeout_ms}")

            #new db owned by this new role
            cur.execute(f"CREATE DATABASE {db_name} OWNER {role_name}")
            db_created = True
            logger.info("Created database", db_name = db_name, owner = role_name)

            #metadata
            cur.execute("""
                        INSERT INTO provisioned_dbs
                        (session_id, db_name, db_role, mode, status)
                        VALUES (%s, %s, %s, %s, %s)
                        """, (session_id or "anonymous", db_name, role_name, "managed", "active"))

            metadata_recorded = True
            logger.info("Recorded metadata", db_name = db_name)
            
        #parse host and port
        import re
        match = re.match(r'postgresql://[^@]+@([^:]+):(\d+)/', admin_dsn)
        
        if match:
            host = match.group(1)
            port = int(match.group(2))
            
        else:
            host = "localhost"
            port = 5432
            
        db_config = DatabaseConfig(
            host = host,
            port = port,
            dbname = db_name,
            user = role_name,
            password = password
        )
        
        #sample data if doing it
        if load_sample and settings.enable_sample_data:
            try:
                _load_sample_data(db_config)
                logger.info("Sample data loaded successfully", db_name = db_name)

            except Exception as e:
                logger.error("Failed to load sample data", db_name = db_name, error = str(e))

                with admin_conn.cursor() as cur:
                    cur.execute("UPDATE provisioned_dbs SET status = %s WHERE db_name = %s", ("error", db_name))

                raise Exception(f"Database created but sample data loading failed: {str(e)}")
            
        return db_config


    
    except Exception as e:
        logger.error("Provisioning failed", db_name = db_name, error = str(e), exc_info = True)

        #clean
        if admin_conn:
            try:
                with admin_conn.cursor() as cur:
                    if db_created:
                        logger.info("Attempting to drop database during cleanup", db_name = db_name)
                        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")

                    if role_created:
                        logger.info("Attempting to drop role during cleanup", role_name = role_name)
                        cur.execute(f"DROP ROLE IF EXISTS {role_name}")

                logger.info("Cleanup completed")

            except Exception as cleanup_error:
                logger.error("Cleanup failed", error = str(cleanup_error))

        raise Exception(f"Failed to provision managed database: {str(e)}")
    
    finally:
        if admin_conn:
            admin_conn.close()

        

def _load_sample_data(db_config: DatabaseConfig) -> None:
    from urllib.parse import quote_plus
    
    encoded_password = quote_plus(db_config.password)
    dsn = f"postgresql://{db_config.user}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.dbname}"

    sql_path = Path(__file__).parent.parent.parent / "infra" / "sql" / "init-sales.sql"

    if not sql_path.exists():
        raise Exception(f"Sample data file not found: {sql_path}")

    with open(sql_path, 'r') as f:
        sample_sql = f.read()

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute(sample_sql)

        #verify loaded
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sales.customers")
            count = cur.fetchone()[0]

            if count == 0:
                raise Exception("Sample data loaded but no customers found")

        logger.info("Sample data loaded", customer_count = count, db_name = db_config.dbname)

    finally:
        if conn:
            conn.close()



def update_db_activity(db_name: str) -> None:
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn

    conn = None
    
    try:
        conn = psycopg2.connect(admin_dsn)
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("""
                        UPDATE provisioned_dbs
                        SET last_used_at = CURRENT_TIMESTAMP
                        WHERE db_name = %s AND status = 'active'
                        """, (db_name,))

            if cur.rowcount > 0:
                logger.debug("Updated activity timestamp", db_name = db_name)

    except Exception as e:
        logger.warning("Failed to update activity timestamp", db_name = db_name, error = str(e))

    finally:
        if conn:
            conn.close()


def deprovision_database(identifier: str) -> None:
    raise NotImplementedError("Database deprovisioning not yet implemented")
