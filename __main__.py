from helpers.load_config import load_config
from helpers.logger import logger
from open_ai.openai_wrapper import get_openai
from rabbitmq.rabbitmq_connection import get_rabbitmq
from rabbitmq.rabbitmq_consumer import subscribe_to_rabbitmq
from rabbitmq.rabbitmq_filler import supabase_to_rabbitmq
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from supabase_helpers.supabase_connection import get_supabase_postgres

if __name__ == "__main__":
    logger.info("Brand name here...")
    config = load_config()
    logger.info("Starting up... Specified mode: %s", config.MODE)

    # Ensure all required services are available before starting
    get_rabbitmq()
    get_supabase_postgres()

    if config.MODE == "consumer":
        logger.info("Starting in consumer mode")
        get_stable_diffusion()
        get_openai()

        subscribe_to_rabbitmq()
    elif config.MODE == "filler":
        logger.info("Starting in filler mode")
        supabase_to_rabbitmq()
    else:
        logger.error("Invalid mode. Make sure you have set the MODE environment variable to either 'consumer' or 'filler'... Aborting startup!")