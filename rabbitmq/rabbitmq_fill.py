import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pika
import json
import sys
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

from helpers.logger import logger

# Load environment variables
load_dotenv()

# Environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE')
RABBITMQ_QUEUE_SIZE = int(os.getenv('RABBITMQ_QUEUE_SIZE', '0')) or None
RABBITMQ_USER = os.getenv('RABBITMQ_USER')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')

SUPABASE_POSTGRES_USER = os.getenv('SUPABASE_POSTGRES_USER')
SUPABASE_POSTGRES_PASSWORD = os.getenv('SUPABASE_POSTGRES_PASSWORD')
SUPABASE_POSTGRES_DB = os.getenv('SUPABASE_POSTGRES_DB')
SUPABASE_POSTGRES_HOST = os.getenv('SUPABASE_POSTGRES_HOST')
SUPABASE_POSTGRES_PORT = os.getenv('SUPABASE_POSTGRES_PORT')

NODE_ID = os.getenv('NODE_ID')

# Initialize and return a PostgreSQL connection with autocommit enabled.
def init_postgres_connection():
    try:
        logger.info(f"PostgreSQL config: %s", {"host": SUPABASE_POSTGRES_HOST, "user": SUPABASE_POSTGRES_USER})
        conn = psycopg2.connect(
            user=SUPABASE_POSTGRES_USER,
            password=SUPABASE_POSTGRES_PASSWORD,
            dbname=SUPABASE_POSTGRES_DB,
            host=SUPABASE_POSTGRES_HOST,
            port=SUPABASE_POSTGRES_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("PostgreSQL Connection successful")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

# Initialize and return a RabbitMQ connection and channel.
def init_rabbitmq_connection():
    try:
        logger.info("RabbitMQ config: %s", {
                    'host': RABBITMQ_HOST,
                    'queue': RABBITMQ_QUEUE,
                    'user': RABBITMQ_USER
                    })

        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials
        ))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        logger.info("RabbitMQ connection successful")
        return connection, channel
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        sys.exit(1)

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
            (NODE_ID, datetime.now().isoformat())
        )
        job = cursor.fetchone()
        if job:
            job_id, request, created_at = job
            logger.info(f"Claimed job {job_id} by node {NODE_ID}")
            return {'request': request, 'created_at': created_at}
        return None
    except Exception as e:
        logger.error(f"Error fetching job from PostgreSQL: {e}")
        return None
    finally:
        cursor.close()

# Update the status of a job in the job_queue table.
def update_job_status(conn, job_id, status):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE job_queue
            SET status = %s
            WHERE id = %s;
            """,
            (status, job_id)
        )
        logger.info(f"Updated job {job_id} status to {status}.")
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")
    finally:
        cursor.close()


# Fetch jobs if RabbitMQ queue is below the threshold
def fetch_jobs_if_needed(conn, channel):
    try:
        queue_state = channel.queue_declare(queue=RABBITMQ_QUEUE, passive=True)
        queue_length = queue_state.method.message_count
        logger.info(f"Current RabbitMQ queue length: {queue_length}")

        while queue_length < RABBITMQ_QUEUE_SIZE:
            logger.info("Queue below threshold, fetching more jobs.")
            job_data = fetch_job_from_supabase(conn)
            if not job_data:
                break

            if validate_job(job_data, conn):
                channel.basic_publish(
                    exchange='',
                    routing_key=RABBITMQ_QUEUE,
                    body=json.dumps(job_data['request']),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                logger.info(f"Job added to RabbitMQ: {job_data['request']}")

            queue_state = channel.queue_declare(queue=RABBITMQ_QUEUE, passive=True)
            queue_length = queue_state.method.message_count
            time.sleep(2)

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")

# Validate job data before adding it to RabbitMQ
def validate_job(job_data):
    created_at = job_data.get('created_at')
    if created_at and datetime.now() - created_at < timedelta(days=1):
        logger.info("Job validation failed: created_at is less than one day old.")
        return False
    return True

# Main function to subscribe to PostgreSQL notifications and send new rows to RabbitMQ
def supabase_to_rabbitmq():
    postgres_conn = init_postgres_connection()
    rabbit_conn, rabbit_channel = init_rabbitmq_connection()

    try:
        while True:
            fetch_jobs_if_needed(postgres_conn, rabbit_channel)
            time.sleep(10)
    finally:
        postgres_conn.close()
        rabbit_conn.close()
        logger.info("Supabase & RabbitMQ connections terminated.")