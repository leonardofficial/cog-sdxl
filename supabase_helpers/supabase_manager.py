from supabase import create_client
from supabase._sync.client import SyncClient
from helpers.load_config import load_config


_supabaseClient: SyncClient = None
def get_supabase():
    config = load_config()

    global _supabaseClient
    if _supabaseClient is None:
        _supabaseClient = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabaseClient