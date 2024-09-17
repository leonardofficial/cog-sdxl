import sys
import pika
from helpers.load_config import load_config
from helpers.logger import logger

config = load_config()
_rabbitmq = None

# Initialize and return a RabbitMQ connection and channel.
def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is not None:
        return _rabbitmq

    try:
        logger.info("RabbitMQ config: %s", {
                    'host': config.RABBITMQ_HOST,
                    'queue': config.RABBITMQ_QUEUE,
                    'user': config.RABBITMQ_DEFAULT_USER
                    })

        credentials = pika.PlainCredentials(config.RABBITMQ_DEFAULT_USER, config.RABBITMQ_DEFAULT_PASS)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=config.RABBITMQ_HOST,
            credentials=credentials
        ))
        channel = connection.channel()
        channel.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)

        logger.info("RabbitMQ connection successful")
        return connection, channel
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}")
        sys.exit(1)
