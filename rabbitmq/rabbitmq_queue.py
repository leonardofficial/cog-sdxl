import pika

from data_types.types import SupabaseJobQueueType
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

# Add a job to the RabbitMQ queue.
def add_job_to_queue(channel, job_data: SupabaseJobQueueType):
    try:
        channel.basic_publish(
            exchange='',
            routing_key=config.RABBITMQ_QUEUE,
            body=job_data.json(),
            properties=pika.BasicProperties(delivery_mode=2, message_id=job_data.id),
        )
        logger.info(f"{job_data.id} - Job added to RabbitMQ Queue")
    except Exception as e:
        logger.error(f"{job_data.id} - Failed to add job to RabbitMQ: {e}")