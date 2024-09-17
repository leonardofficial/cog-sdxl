import sys
import time
import pika
from helpers.load_config import load_config
from helpers.logger import logger
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker

config = load_config()
_rabbitmq = None
RECONNECT_DELAY = 5  # seconds

# Universal function for RabbitMQ setup
def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is not None:
        return _rabbitmq

    while True:
        try:
            logger.info("Connecting to RabbitMQ...")

            # Set up RabbitMQ connection with username and password credentials
            credentials = pika.PlainCredentials(
                username=config.RABBITMQ_DEFAULT_USER,
                password=config.RABBITMQ_DEFAULT_PASS
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config.RABBITMQ_HOST,
                    credentials=credentials,
                    heartbeat=60,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)

            logger.info(f"Connected to RabbitMQ and declared queue: {config.RABBITMQ_QUEUE}")
            _rabbitmq = connection, channel

            return connection, channel
        except (AMQPConnectionError, ChannelClosedByBroker) as e:
            logger.error(f"Connection error: {e}. Reconnecting in {RECONNECT_DELAY} seconds...")
            time.sleep(RECONNECT_DELAY)
        except Exception as e:
            logger.exception(f"Unexpected error occurred: {e}")
            break
        finally:
            close_connection(connection, channel)
            sys.exit(1)

# Utility function to close RabbitMQ connection and channel
def close_connection(connection, channel):
    try:
        if channel and channel.is_open:
            channel.close()
        if connection and connection.is_open:
            connection.close()
        logger.info("Connection to RabbitMQ closed.")
    except Exception as close_error:
        logger.error(f"Failed to close RabbitMQ connection: {close_error}")