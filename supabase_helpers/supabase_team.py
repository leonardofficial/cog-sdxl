from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase_postgres

def team_nsfw_allowed(team_id: str) -> bool:
    try:
        supabase = get_supabase_postgres()
        cursor = supabase.cursor()
        cursor.execute("SELECT id FROM teams WHERE id = %s AND nsfw_allowed = TRUE", (team_id,))
        data = cursor.fetchall()
        return len(data) > 0
    except Exception as e:
        logger.error("Failed to fetch team from database for NSFW check. Defaulting to NSFW disabled: ", e)
        return False