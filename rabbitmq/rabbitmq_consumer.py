import json
from data_types.types import SupabaseJobQueueType
from generate.text_to_image import text_to_image
from generate.text_to_portrait import text_to_portrait
from helpers.execution_info import create_execution_info
from helpers.load_config import load_config
import pika
import time
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker
from helpers.logger import logger
from rabbitmq.rabbitmq_connection import get_rabbitmq
from rabbitmq.rabbitmq_queue import get_queue_length
from supabase_helpers.update_job_queue import update_job_queue

config = load_config()

# Subscribe to RabbitMQ and consume messages from the queue
def subscribe_to_rabbitmq():
    connection, channel = get_rabbitmq()
    channel.basic_consume(
        queue=config.RABBITMQ_QUEUE,
        on_message_callback=consume_queue,
        auto_ack=False  # set to False for manual ack to handle failures properly
    )
    channel.start_consuming()

# Callback function to process messages from the queue.
def consume_queue(ch, method, properties, body):
    try:
        # Process the messages
        decoded_body = body.decode('utf-8')
        process_message(decoded_body)

        # Acknowledge the message only after successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.exception(f"Failed to process task, error: {e}")
        update_job_queue(decoded_body.id, 'failed', None, {"error": e})
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Process the message body
def process_message(body):
    task_data = SupabaseJobQueueType.from_json(json.loads(body))
    logger.info(f"Processing Job {task_data.id}")

    start_time = time.time()

    try:
        if task_data.request.type == "text-to-image":
            response = text_to_image(task_data.request)
        elif task_data.request.type == "text-to-portrait":
            response = text_to_portrait(task_data.request)
        else:
            logger.error(f"Unsupported task type: {task_data.request.type}")
            return

        execution_info = create_execution_info(start_time)
        update_job_queue(task_data.id, 'succeeded', response, execution_info)
    except Exception as e:
        logger.exception(f"Error processing task ID: {task_data.id}, error: {e}")
        #supabaseClient.from_('job_queue').update({'status': 'failed', "execution_info": create_execution_info(start_time)}).eq('id', task_id).execute()
