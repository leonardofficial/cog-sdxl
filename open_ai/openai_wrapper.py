import sys
from openai.types import Moderation
from helpers.load_config import load_config
from openai import OpenAI
from helpers.logger import logger

config = load_config()
_openai: OpenAI = None

def get_openai():
    global _openai

    if _openai is None:
        try:
            logger.info("Creating OpenAI Client...")
            _openai = OpenAI(api_key=config.OPENAI_KEY)
            logger.info("OpenAI Client was created successfully")
        except Exception as e:
            logger.error("OpenAI Client could not be created: ", e)
            sys.exit(1)
    return _openai

def openai_moderate(prompt: str) -> Moderation:
    openai = get_openai()
    try:
        response = openai.moderations.create(input=prompt)
        results = response.results[0]
        return results
    except Exception as e:
        logger.error(f"Failed to request moderation from OpenAI, error: {e}")
        raise Exception("Endpoint connection not possible")