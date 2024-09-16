import pika
import sys
import time
from datetime import datetime, timedelta, timezone
from data_types.types import SupabaseJobQueueType, TextToImageRequestType
from helpers.load_config import load_config
from helpers.logger import logger
from rabbitmq.rabbitmq_helpers import get_queue_length
from supabase_helpers.supabase_manager import get_supabase_postgres
from supabase_helpers.update_job_queue import update_job_queue

config = load_config()

# Initialize and return a RabbitMQ connection and channel.
def init_rabbitmq_connection():
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

# Validate job data before adding it to RabbitMQ
def validate_supabase_job_data(job_data: SupabaseJobQueueType):
    try:
        created_at = job_data.created_at
        if created_at and ((datetime.now(timezone.utc) - created_at) > timedelta(minutes=config.JOB_DISCARD_THRESHOLD)):
            update_job_queue(job_data.id, 'stopped', None, {"error": "expired (job too long in queue)"})
            return False
        return True
    except Exception as e:
        logger.error(f"{job_data.id} - Job validation raised exception: {e}")
        return False

# Fetch a job from the job_queue table in PostgreSQL.
def fetch_job_from_supabase(conn) -> SupabaseJobQueueType:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE job_queue
            SET status = 'assigned',
                execution_info = jsonb_set(
                    COALESCE(execution_info, '{}'),
                    '{node}',
                    to_jsonb(%s::text),
                    true
                ) || jsonb_build_object('assigned_at', %s::text)
            WHERE id = (
                SELECT id FROM job_queue
                WHERE status = 'queued'
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id, request, created_at;
            """,
            (config.NODE_ID, datetime.now().isoformat())
        )
        job = cursor.fetchone()
        if job:
            job_id, request, created_at = job
            job_data = SupabaseJobQueueType(
                id=job_id,
                request=TextToImageRequestType.from_json(request),
                created_at=created_at,
                status='assigned'
            )
            logger.info(f"Assigned job {job_id} to node {config.NODE_ID}")
            return job_data
        return None
    except Exception as e:
        logger.error(f"Error fetching job from PostgreSQL: {e}")
        return None
    finally:
        cursor.close()

# Fetch jobs if RabbitMQ queue is below the threshold
def fetch_jobs_if_needed(conn, channel):
    try:
        queue_length = get_queue_length(channel)
        logger.info(f"Current RabbitMQ queue length: {queue_length}")

        while queue_length < config.RABBITMQ_QUEUE_SIZE:
            logger.info(f"Queue below threshold ({config.RABBITMQ_QUEUE_SIZE}), fetching more jobs.")
            job_data = fetch_job_from_supabase(conn)
            if not job_data:
                break

            if validate_supabase_job_data(job_data):
                add_job_to_rabbitmq(channel, job_data)

            queue_length = get_queue_length(channel)
            time.sleep(2)

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")

# Add a job to the RabbitMQ queue.
def add_job_to_rabbitmq(channel, job_data: SupabaseJobQueueType):
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

# Main function to subscribe to PostgreSQL notifications and send new rows to RabbitMQ
def supabase_to_rabbitmq():
    supabase_postgres = get_supabase_postgres()
    rabbit_conn, rabbit_channel = init_rabbitmq_connection()

    logger.info("Stopping jobs older than %s minutes", config.JOB_DISCARD_THRESHOLD)

    try:
        while True:
            fetch_jobs_if_needed(supabase_postgres, rabbit_channel)
            time.sleep(10)
    finally:
        supabase_postgres.close()
        rabbit_conn.close()
        logger.info("Supabase & RabbitMQ connections terminated.")