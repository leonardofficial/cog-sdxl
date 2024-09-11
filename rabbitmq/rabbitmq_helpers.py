from helpers.load_config import load_config
from helpers.logger import logger

config = load_config()

# Get the length of the RabbitMQ queue.
def get_queue_length(channel):
    try:
        queue_state = channel.queue_declare(queue=config.RABBITMQ_QUEUE, passive=True)
        return queue_state.method.message_count
    except Exception as e:
        logger.error(f"Failed to get local RabbitMQ queue length: {e}")
        return None
