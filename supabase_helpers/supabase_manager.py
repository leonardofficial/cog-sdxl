from supabase import create_client
from helpers.load_config import load_config

config = load_config()

supabaseClient = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
