from helpers.logger import logger
from rabbitmq.rabbitmq_consumer import subscribe_to_rabbitmq
from rabbitmq.rabbitmq_filler import supabase_to_rabbitmq
from dotenv import load_dotenv
import os

from stable_diffusion.stable_diffusion_manager import get_stable_diffusion

load_dotenv()

# Read variables
MODE = os.getenv('MODE')

if __name__ == "__main__":
    logger.info("Brand name here...")
    logger.info("Starting up... Specified mode: %s", MODE)

    if MODE == "consumer":
        logger.info("Starting in consumer mode")
        get_stable_diffusion() # Ensure the Stable Diffusion model is loaded before starting the consumer
        subscribe_to_rabbitmq()
    elif MODE == "filler":
        logger.info("Starting in filler mode")
        supabase_to_rabbitmq()
    else:
        logger.error("Invalid mode. Make sure you have set the MODE environment variable to either 'consumer' or 'filler'... Aborting startup!")