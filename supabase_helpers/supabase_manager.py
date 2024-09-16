import sys

import psycopg2
from supabase import create_client
from supabase._sync.client import SyncClient
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from helpers.load_config import load_config
from helpers.logger import logger

config = load_config()
_supabaseClient: SyncClient = None
_supabasePostgres = None

def get_supabase():
    global _supabaseClient
    if _supabaseClient is None:
        _supabaseClient = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabaseClient


# Initialize and return a PostgreSQL connection with autocommit enabled.
def get_supabase_postgres():
    global _supabasePostgres

    if _supabasePostgres is not None:
        return _supabasePostgres

    try:
        logger.info(f"Connecting to PostgreSQL with config: %s", {"host": config.SUPABASE_POSTGRES_HOST, "user": config.SUPABASE_POSTGRES_USER})

        conn = psycopg2.connect(
            user=config.SUPABASE_POSTGRES_USER,
            password=config.SUPABASE_POSTGRES_PASSWORD,
            dbname=config.SUPABASE_POSTGRES_DB,
            host=config.SUPABASE_POSTGRES_HOST,
            port=config.SUPABASE_POSTGRES_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        logger.info("PostgreSQL connection successful")
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        sys.exit(1)


