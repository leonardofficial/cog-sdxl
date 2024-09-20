import json
from datetime import datetime
from data_types.types import SupabaseJobQueueType, JobStatus, JobType
from generate.text_to_image import text_to_image
from generate.text_to_portrait import text_to_portrait
from helpers.execution_metadata import create_execution_metadata
from helpers.load_config import load_config
from helpers.logger import logger
from rabbitmq.rabbitmq_connection import get_rabbitmq
from supabase_helpers.supabase_images import create_supabase_image_entities
from supabase_helpers.supabase_job_queue import update_supabase_job_queue

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
    logger.info("Started consuming messages from the queue.")

# Callback function to process messages from the queue.
def consume_queue(ch, method, properties, body):
    start_time = datetime.now()
    try:
        # Process the messages
        decoded_body = body.decode('utf-8')
        process_message(decoded_body)

        # Acknowledge the message only after successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        task_id = json.loads(decoded_body).get('id')
        logger.exception(f"Failed to process task {task_id}, error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        estimated_runtime = int((datetime.now() - start_time).total_seconds() * 1000) # Add rough execution time for debugging (it counts storage upload time as well, hence not accurate)
        update_supabase_job_queue(task_id, JobStatus.FAILED, create_execution_metadata(estimated_runtime, {"error": str(e)}))

# Process the message body
def process_message(body):
    global executions
    task_data = SupabaseJobQueueType.from_json(json.loads(body))
    logger.info(f"Processing Job {task_data.id}")

    # [1/3] Generate image
    try:
        if task_data.job_type == JobType.TEXT_TO_IMAGE:
            executions = text_to_image(task_data)
        elif task_data.job_type == JobType.TEXT_TO_PORTRAIT:
            executions = text_to_portrait(task_data.request_data)
        else:
            raise Exception(f"invalid job type: {task_data.job_type}")
    except Exception:
        raise Exception(f"Image generation failed")

    if len(executions) != task_data.request_data.num_options:
        raise Exception(f"Number of generated images ({len(executions)}) did not match the request ({task_data.request_data.num_options})")

    # [2/3] Create images in Supabase
    try:
        create_supabase_image_entities(executions, task_data)
    except Exception:
        raise Exception(f"Image upload failed")

    # [3/3] Update database job_queue
    try:
        total_runtime = sum(execution.runtime for execution in executions)
        execution_metadata = create_execution_metadata(total_runtime)
        update_supabase_job_queue(task_data.id, JobStatus.SUCCEEDED, execution_metadata)
    except Exception:
        raise Exception(f"Database update failed")
