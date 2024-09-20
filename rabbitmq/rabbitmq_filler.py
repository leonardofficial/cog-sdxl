import time
from datetime import datetime, timedelta, timezone
from data_types.types import SupabaseJobQueueType, TextToImageRequestType, JobStatus, JobType
from helpers.load_config import load_config
from helpers.logger import logger
from rabbitmq.rabbitmq_connection import get_rabbitmq
from rabbitmq.rabbitmq_queue import get_queue_length, add_job_to_queue
from supabase_helpers.supabase_connection import get_supabase_postgres
from supabase_helpers.supabase_job_queue import update_supabase_job_queue

config = load_config()

# Main function to subscribe to PostgreSQL notifications and send new rows to RabbitMQ
def supabase_to_rabbitmq():
    supabase_postgres = get_supabase_postgres()
    rabbit_conn, rabbit_channel = get_rabbitmq()

    logger.info("Stopping jobs older than %s minutes", config.JOB_DISCARD_THRESHOLD)

    try:
        while True:
            fetch_jobs_if_needed(supabase_postgres, rabbit_channel)
            time.sleep(10)
    finally:
        supabase_postgres.close()
        rabbit_conn.close()
        logger.info("Supabase & RabbitMQ connections terminated.")

# Validate job data before adding it to RabbitMQ
def validate_supabase_job_data(job_data: SupabaseJobQueueType):
    try:
        created_at = job_data.created_at
        if created_at and ((datetime.now(timezone.utc) - created_at) > timedelta(minutes=config.JOB_DISCARD_THRESHOLD)):
            update_supabase_job_queue(job_data.id, JobStatus.FAILED, {"error": "expired"})
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
            SET job_status = 'assigned',
                execution_metadata = jsonb_set(
                    COALESCE(execution_metadata, '{}'),
                    '{node}',
                    to_jsonb(%s::text),
                    true
                ) || jsonb_build_object('assigned_at', %s::text)
            WHERE id = (
                SELECT id FROM job_queue
                WHERE job_status = 'queued'
                ORDER BY created_at ASC 
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id, job_type, request_data, team, created_at;
            """,
            (config.NODE_ID, datetime.now().isoformat())
        )
        job = cursor.fetchone()
        if job:
            job_id, job_type, request_data, team, created_at = job
            job_data = SupabaseJobQueueType(
                id=job_id,
                request_data=TextToImageRequestType.from_json(request_data),
                created_at=created_at,
                job_status='assigned',
                team=team,
                job_type=JobType(job_type)
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
                add_job_to_queue(channel, job_data)

            queue_length = get_queue_length(channel)
            time.sleep(2)

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")