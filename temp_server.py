from flask import Flask, request, send_file, jsonify
from io import BytesIO
import torch
from diffusers import DiffusionPipeline, ControlNetModel
import random
import logging
import time
import json
from tqdm import tqdm
from PIL import Image
from supabase import create_client, Client, SupabaseRealtimeClient
from realtime.connection import Socket
import threading

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Initialize Supabase client
SUPABASE_ID = "hccopskgtcodsnjpivvo"
SUPABASE_URL = "https://hccopskgtcodsnjpivvo.supabase.co"
SUPABASE_KEY = ""
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_device():
    """
    Check if CUDA is available and return the appropriate device.
    """
    if torch.cuda.is_available():
        logger.info("CUDA is available. Using GPU.")
        return "cuda"
    else:
        logger.error("CUDA is not available. Using CPU. This may lead to inefficient performance.")
        return "cpu"

# Execute the device detection at the beginning
device = get_device()

# Load the Stable Diffusion XL model
model_id = "SG161222/RealVisXL_V4.0"
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
pipe = pipe.to(device)

# Load the ControlNet model and local image
controlnet_model_id = "thibaud/controlnet-openpose-sdxl-1.0"
controlnet = ControlNetModel.from_pretrained(controlnet_model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
controlnet = controlnet.to(device)
control_image = Image.open("portrait.png")

def custom_progress_callback(step: int, t: int, latents):
    progress = (step + 1) / t * 100
    progress_bar = f"{progress:.2f}%"
    tqdm.write(f"{progress_bar} - {time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Progress: Step {step + 1} ({progress:.2f}%)")

def generate_random_seed():
    return random.randint(0, 2**32 - 1)

def process_task(task):
    task_id = task['id']
    task_data = task.get("request", {})
    logger.info(f"Processing task ID: {task_id} with data: {task_data}")

    try:
        supabase.from_('job_queue').update({'status': 'running'}).eq('id', task_id).execute()
        generate_image(task_data)
        supabase.from_('job_queue').update({'status': 'succeeded'}).eq('id', task_id).execute()
    except Exception as e:
        logger.exception(f"Error processing task ID: {task_id}, error: {e}")
        supabase.from_('job_queue').update({'status': 'failed'}).eq('id', task_id).execute()

def generate_image(data):
    if not data:
        logger.error("Data is required")
        raise ValueError("Data is required")

    start_time = time.time()

    prompt = data.get('prompt', None)
    negative_prompt = data.get('negative_prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    num_inference_steps = data.get('num_inference_steps', 50)
    seed = data.get('seed', generate_random_seed())
    use_controlnet = data.get('use_controlnet', False)

    request_parameters = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "cfg": cfg,
        "width": width,
        "height": height,
        "num_inference_steps": num_inference_steps,
        "seed": seed,
        "use_controlnet": use_controlnet
    }
    logger.info(f"Request with parameters: {json.dumps(request_parameters)}")

    if not prompt:
        logger.error("Prompt is required")
        raise ValueError("Prompt is required")

    with torch.no_grad():
        generator = torch.manual_seed(seed)
        try:
            with tqdm(total=num_inference_steps, desc="Generating", unit="step") as pbar:
                def progress_callback(step, t, latents):
                    custom_progress_callback(step, t, latents)
                    pbar.update(1)

                if use_controlnet:
                    logger.info("Using ControlNet for image generation")
                    pipe.controlnet_model = controlnet
                    image = pipe(
                        prompt,
                        negative_prompt=negative_prompt,
                        guidance_scale=cfg,
                        generator=generator,
                        height=height,
                        width=width,
                        num_inference_steps=num_inference_steps,
                        control_image=control_image,
                        callback=progress_callback,
                        callback_steps=1
                    ).images[0]
                else:
                    logger.info("Generating image without ControlNet")
                    pipe.controlnet_model = None
                    image = pipe(
                        prompt,
                        negative_prompt=negative_prompt,
                        guidance_scale=cfg,
                        generator=generator,
                        height=height,
                        width=width,
                        num_inference_steps=num_inference_steps,
                        callback=progress_callback,
                        callback_steps=1
                    ).images[0]
        except Exception as e:
            logger.exception("Error during image generation")
            raise e

        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

        # Upload image to Supabase storage
        storage_response = supabase.storage.from_("models").upload(f"{time.time()}.png", img_io.read())
        storage_id = storage_response.get("Key")
        if not storage_id:
            logger.error("Failed to upload image to Supabase storage")
            raise ValueError("Failed to upload image to Supabase storage")

    elapsed_time = time.time() - start_time
    logger.info(f"Image generated and uploaded successfully in {elapsed_time:.2f} seconds, storage ID: {storage_id}")
    return storage_id

# @app.route('/generate', methods=['POST'])
# def add_to_queue():
#     data = request.json
#
#     if not data.get('prompt'):
#         logger.error("Prompt is required")
#         return jsonify({"error": "Prompt is required"}), 400
#
#     task = {
#         "data": json.dumps(data),
#         "status": "pending"
#     }
#
#     try:
#         response = supabase.from_('job_queue').insert(task).execute()
#         task_id = response.data[0]['id']
#         logger.info(f"Task added to queue with ID: {task_id}")
#         return jsonify({"task_id": task_id}), 200
#     except Exception as e:
#         logger.exception("Error adding task to queue")
#         return jsonify({"error": str(e)}), 500

def subscribe_to_queue():
    def on_insert(payload):
        new_task = payload["record"]
        if new_task['status'] == 'queued':
            process_task(new_task)

    url = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
    s = Socket(url)
    s.connect()

    channel_1 = s.set_channel("realtime:public:job_queue")
    channel_1.join().on("INSERT", on_insert)
    s.listen()

if __name__ == '__main__':
    subscribe_to_queue()
    app.run(host='0.0.0.0', port=5000)