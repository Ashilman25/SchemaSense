#!/usr/bin/env python3
#ttl based script for cleaning up provisioned dbs
#finds and remove after period of time


import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from app.config import get_settings
from app.utils.logging_utils import get_secure_logger

logger = get_secure_logger(__name__)

#find and clean dbs after ttl_days
def cleanup_stale_databases(dry_run: bool = False, ttl_days: int = 14):
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn
    
    if not admin_dsn:
        logger.error("MANAGED_PG_ADMIN_DSN not configured")
        return 0
    
    cutoff_time = datetime.now() - timedelta(days = ttl_days)
    logger.info(f"Starting TTL cleanup", dry_run = dry_run, ttl_days = ttl_days, cutoff_time = cutoff_time.isoformat())
    
    conn = None
    cleaned_count = 0
    
    try:
        conn = psycopg2.connect(admin_dsn)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT id, session_id, db_name, db_role, last_used_at
                        FROM provisioned_dbs
                        WHERE status = 'active' AND last_used_at < %s
                        ORDER BY last_used_at ASC
                        """, (cutoff_time,))
            stale_dbs = cur.fetchall()
            
        if not stale_dbs:
            logger.info("No stale databases found")
            return 0
        
        logger.info(f"Found {len(stale_dbs)} stale databases")
        
        #clean up each
        for db_id, session_id, db_name, db_role, last_used_at in stale_dbs:
            age_days = (datetime.now() - last_used_at).days
            
            logger.info(
                "Processing stale database",
                db_id = db_id,
                db_name = db_name,
                session_id = session_id,
                last_used_at = last_used_at.isoformat(),
                age_days = age_days,
                dry_run = dry_run
            )
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete database: {db_name} (age: {age_days} days)")
                cleaned_count += 1
                continue
            
            try:
                with conn.cursor() as cur:
                    logger.info(f"Terminating connections to {db_name}")
                    cur.execute("""
                                SELECT pg_terminate_backend(pid)
                                FROM pg_stat_activity
                                WHERE datname = %s AND pid <> pg_backend_pid()
                                """, (db_name,))
                    
                    #drop db
                    logger.info(f"Dropping database {db_name}")
                    cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
                    
                    #drop role
                    logger.info(f"Dropping role {db_role}")
                    cur.execute(f"DROP ROLE IF EXISTS {db_role}")
                    
                    #update meta data
                    cur.execute("""
                                UPDATE provisioned_dbs
                                SET status = 'deleted'
                                WHERE id = %s
                                """, (db_id,))
                    
                    
                logger.info(
                    "Successfully cleaned up database",
                    db_name = db_name,
                    db_id = db_id,
                    age_days = age_days
                )
                
                cleaned_count += 1
                    
            
            except Exception as e:
                logger.error(
                    "Failed to clean up database",
                    db_name = db_name,
                    db_id = db_id,
                    error = str(e),
                    exc_info = True
                )
                
                continue
            
        logger.info(
            "TTL cleanup completed",
            cleaned_count = cleaned_count,
            dry_run = dry_run
        )
        
        return cleaned_count
                
    
    except Exception as e:
        logger.error("TTL cleanup failed", error = str(e), exc_info = True)
        raise

    
    finally:
        if conn:
            conn.close()



def main():
    parser = argparse.ArgumentParser(description = "Clean up provisioned databases that have exceeded their TTL")
    parser.add_argument(
        "--dry-run",
        action = "store_true",
        help = "Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--ttl-days",
        type = int,
        default = None,
        help = "Override TTL days from environment (default: from TTL_CLEANUP_DAYS env or 7)"
    )

    args = parser.parse_args()

    # Get TTL from args, environment, or default
    ttl_days = args.ttl_days
    if ttl_days is None:
        ttl_days = int(os.environ.get("TTL_CLEANUP_DAYS", "14"))

    try:
        cleaned = cleanup_stale_databases(dry_run = args.dry_run, ttl_days = ttl_days)

        if args.dry_run:
            print(f"\n[DRY RUN] Would clean up {cleaned} stale database(s)")
            
        else:
            print(f"\nSuccessfully cleaned up {cleaned} stale database(s)")

        return 0

    except Exception as e:
        print(f"\nError during cleanup: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())