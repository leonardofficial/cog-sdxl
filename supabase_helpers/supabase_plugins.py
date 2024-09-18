from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase

def get_plugins_from_supabase():
    try:
        logger.info("Fetching an up-to-date list of plugins from Supabase...")
        supabase = get_supabase()
        plugins = supabase.table("plugins").select("id").execute()
        return [plugin["id"] for plugin in plugins["data"]]
    except Exception as e:
        logger.exception("Failed to fetch plugins from Supabase: ", e)
        raise e