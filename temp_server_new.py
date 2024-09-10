import time
from supabase_helpers.supabase_manager import supabaseClient
from generate.text_to_image import text_to_image
from helpers.logger import logger
from realtime.connection import Socket
from dotenv import load_dotenv
import os

from temp_server import create_execution_info

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_ID = os.getenv('SUPABASE_ID')

# Process task of supabase_helpers queue
def process_task(task):
    task_id = task['id']
    task_data = task.get("request", {})
    logger.info(f"Processing task ID: {task_id} with data: {task_data}")

    start_time = time.time()

    try:
        supabaseClient.from_('job_queue').update({'status': 'running'}).eq('id', task_id).execute()
        generation_response = text_to_image(task_data)
        execution_info = create_execution_info(start_time)
        supabaseClient.from_('job_queue').update({'status': 'succeeded', "response": generation_response, "execution_info": execution_info}).eq('id', task_id).execute()
        logger.info(f"Task {task_id} processed in {execution_info.get('ms') / 1000:.2f} seconds, with response: {generation_response}")
    except Exception as e:
        logger.exception(f"Error processing task ID: {task_id}, error: {e}")
        supabaseClient.from_('job_queue').update({'status': 'failed', "execution_info": create_execution_info(start_time)}).eq('id', task_id).execute()

# Subscribe to supabase_helpers job queue
def subscribe_to_queue_new():
    logger.info(f"Connecting to Supabase with ID {SUPABASE_ID}")
    def on_insert(payload):
        new_task = payload["record"]
        if new_task['status'] == 'queued':
            process_task(new_task)

    try:
        url = f"wss://{SUPABASE_ID}.supabase_helpers.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
        s = Socket(url)
        s.connect()

        channel_1 = s.set_channel("realtime:public:job_queue")
        channel_1.join().on("INSERT", on_insert)
        s.listen()
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {e}")
        raise ValueError("Error connecting to Supabase")