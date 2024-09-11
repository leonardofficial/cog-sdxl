from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

# Read variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_ID = os.getenv('SUPABASE_ID')
NODE_GPU = os.getenv('NODE_GPU')

supabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)
