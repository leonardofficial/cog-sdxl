from helpers.logger import logger
from rabbitmq.rabbitmq_fill import supabase_to_rabbitmq
from temp_server_new import subscribe_to_queue_new
from dotenv import load_dotenv
import os

load_dotenv()

# Read variables
MODE = os.getenv('MODE')

if __name__ == "__main__":
    if MODE == 'consumer':
        logger.info("Starting in consumer mode")
        subscribe_to_queue_new()
    elif MODE == 'filler':
        logger.info("Starting in filler mode")
        supabase_to_rabbitmq()
    else:
        raise ValueError("Invalid mode")