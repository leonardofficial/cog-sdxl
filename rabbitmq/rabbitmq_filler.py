import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pika
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from helpers.load_config import load_config
from helpers.logger import logger
from rabbitmq.rabbitmq_helpers import get_queue_length

config = load_config()

# Initialize and return a PostgreSQL connection with autocommit enabled.
def init_postgres_connection():
    try:
        logger.info(f"PostgreSQL config: %s", {"host": config.SUPABASE_POSTGRES_HOST, "user": config.SUPABASE_POSTGRES_USER})

        conn = psycopg2.connect(
            user=config.SUPABASE_POSTGRES_USER,
            password=config.SUPABASE_POSTGRES_PASSWORD,
            dbname=config.SUPABASE_POSTGRES_DB,
            host=config.SUPABASE_POSTGRES_HOST,
            port=config.SUPABASE_POSTGRES_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        logger.info("PostgreSQL connection successful")
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        sys.exit(1)

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
def validate_supabase_job_data(job_data, conn):
    try:
        created_at = job_data.get('created_at')
        if created_at and ((datetime.now(timezone.utc) - created_at) > timedelta(minutes=config.JOB_DISCARD_THRESHOLD)):
            update_job_status(conn, job_data['id'], 'stopped', {"error": "expired (job too long in queue)"})
            logger.info(f"{job_data['id']} - Job is too old, updating database status to 'stopped'.")
            return False
        return True
    except Exception as e:
        logger.error(f"{job_data['id']} - Job validation raised exception: {e}")
        return False

# Fetch a job from the job_queue table in PostgreSQL.
def fetch_job_from_supabase(conn):
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
            job_data = {
                'id': job_id,
                'request': request,
                'created_at': created_at
            }
            logger.info(f"Assigned job {job_id} to node {config.NODE_ID}")
            return job_data
        return None
    except Exception as e:
        logger.error(f"Error fetching job from PostgreSQL: {e}")
        return None
    finally:
        cursor.close()

# Update the status of a job in the job_queue table.
def update_job_status(conn, job_id, status, execution_info_update=None):
    cursor = conn.cursor()
    try:
        sql = """
            UPDATE job_queue
            SET status = %s
        """
        params = [status]

        if execution_info_update is not None:
            # Convert execution_info_update to JSON string
            execution_info_update_json = json.dumps(execution_info_update)
            sql += ", execution_info = COALESCE(execution_info, '{}'::jsonb) || %s::jsonb"
            params.append(execution_info_update_json)

        sql += " WHERE id = %s;"
        params.append(job_id)

        cursor.execute(sql, tuple(params))
        logger.info(f"Updated job {job_id} status to {status}.")

        if execution_info_update:
            logger.info(f"Appended response update to job {job_id}: {execution_info_update}")
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")
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

            if validate_supabase_job_data(job_data, conn):
                add_job_to_rabbitmq(channel, job_data)

            queue_length = get_queue_length(channel)
            time.sleep(2)

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")

# Add a job to the RabbitMQ queue.
def add_job_to_rabbitmq(channel, job_data):
    try:
        channel.basic_publish(
            exchange='',
            routing_key=config.RABBITMQ_QUEUE,
            body=json.dumps(job_data),
            properties=pika.BasicProperties(delivery_mode=2, message_id=job_data['id']),
        )
        logger.info(f"{job_data['id']} - Job added to RabbitMQ Queue: {job_data}")
    except Exception as e:
        logger.error(f"{job_data['id']} - Failed to add job to RabbitMQ: {e}")

# Main function to subscribe to PostgreSQL notifications and send new rows to RabbitMQ
def supabase_to_rabbitmq():
    postgres_conn = init_postgres_connection()
    rabbit_conn, rabbit_channel = init_rabbitmq_connection()

    logger.info("Stopping jobs older than %s minutes", config.JOB_DISCARD_THRESHOLD)

    try:
        while True:
            fetch_jobs_if_needed(postgres_conn, rabbit_channel)
            time.sleep(10)
    finally:
        postgres_conn.close()
        rabbit_conn.close()
        logger.info("Supabase & RabbitMQ connections terminated.")