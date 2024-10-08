from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase, get_supabase_postgres


def get_plugins_from_supabase():
    try:
        logger.info("Fetching an up-to-date list of plugins from Supabase...")
        supabase = get_supabase_postgres()
        cursor = supabase.cursor()
        cursor.execute("SELECT id FROM plugins")
        data = cursor.fetchall()
        plugin_ids = [t[0] for t in data]
        return plugin_ids
    except Exception as e:
        logger.exception("Failed to fetch plugins from Supabase: ", e)
        raise e