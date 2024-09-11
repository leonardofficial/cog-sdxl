from helpers.logger import logger
from rabbitmq.rabbitmq_fill import supabase_to_rabbitmq
from dotenv import load_dotenv
import os

load_dotenv()

# Read variables
MODE = os.getenv('MODE')

if __name__ == "__main__":
    logger.info("Brand name here...")
    logger.info("Starting up... Specified mode: %s", MODE)

    if MODE == "consumer":
        logger.info("Starting in consumer mode")
    elif MODE == "filler":
        logger.info("Starting in filler mode")
        supabase_to_rabbitmq()
    else:
        logger.error("Invalid mode. Make sure you have set the MODE environment variable to either 'consumer' or 'filler'... Aborting startup!")