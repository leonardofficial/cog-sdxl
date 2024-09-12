import json

from data_types.types import SupabaseJobQueueType
from generate.text_to_image import text_to_image
from helpers.load_config import load_config
import pika
import time
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker
from helpers.logger import logger
from rabbitmq.rabbitmq_helpers import get_queue_length

# Load configuration settings
config = load_config()
RECONNECT_DELAY = 5  # seconds

# Subscribe to RabbitMQ and consume messages from the queue
def subscribe_to_rabbitmq():
    while True:
        try:
            logger.info("Connecting to RabbitMQ...")

            # Set up the RabbitMQ connection with username and password credentials
            credentials = pika.PlainCredentials(
                username=config.RABBITMQ_DEFAULT_USER,
                password=config.RABBITMQ_DEFAULT_PASS
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config.RABBITMQ_HOST,
                    credentials=credentials,
                    heartbeat=60,  # set heartbeat to detect dead connections
                    blocked_connection_timeout=300  # set a timeout for blocked connections
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)

            logger.info(f"Subscribed to queue: {config.RABBITMQ_QUEUE}")
            logger.info("Current queue length: %d", get_queue_length(channel))
            channel.basic_consume(
                queue=config.RABBITMQ_QUEUE,
                on_message_callback=consume_queue,
                auto_ack=False  # set to False for manual ack to handle failures properly
            )
            channel.start_consuming()

        except (AMQPConnectionError, ChannelClosedByBroker) as e:
            logger.error(f"Connection error: {e}. Reconnecting in {RECONNECT_DELAY} seconds...")
            time.sleep(RECONNECT_DELAY)
        except Exception as e:
            logger.exception(f"Unexpected error occurred: {e}")
            break
        finally:
            try:
                if channel.is_open:
                    channel.close()
                if connection.is_open:
                    connection.close()
                logger.info("Connection to RabbitMQ closed.")
            except Exception as close_error:
                logger.error(f"Error closing connection: {close_error}")

# Callback function to process messages from the queue.
def consume_queue(ch, method, properties, body):
    try:
        logger.info(f"Received task from queue: {body}")

        # Process the messages
        decoded_body = body.decode('utf-8')
        process_message(decoded_body)

        # Acknowledge the message only after successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.exception(f"Failed to process task: {e}")
        # Optional: Implement logic to requeue or discard the message based on the error
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Process the message body
def process_message(body):
    task_data = SupabaseJobQueueType.from_json(json.loads(body))
    logger.info(f"Processing Job {task_data.id}")

    start_time = time.time()

    try:
        #supabaseClient.from_('job_queue').update({'status': 'running'}).eq('id', task_id).execute()
        generation_response = text_to_image(task_data.request)
        logger.info(f"Generation response: {generation_response}")
        #execution_info = create_execution_info(start_time)
       # supabaseClient.from_('job_queue').update({'status': 'succeeded', "response": generation_response, "execution_info": execution_info}).eq('id', task_id).execute()
        # logger.info(f"Task {task_id} processed in {execution_info.get('ms') / 1000:.2f} seconds, with response: {generation_response}")
    except Exception as e:
        logger.exception(f"Error processing task ID: {task_data.id}, error: {e}")
        #supabaseClient.from_('job_queue').update({'status': 'failed', "execution_info": create_execution_info(start_time)}).eq('id', task_id).execute()
