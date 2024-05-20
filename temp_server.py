from io import BytesIO
import torch
from diffusers import DiffusionPipeline, ControlNetModel
import random
import logging
import time
import json
from tqdm import tqdm
from PIL import Image
from supabase import create_client, Client
from realtime.connection import Socket
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Read variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_ID = os.getenv('SUPABASE_ID')
DEVICE = os.getenv('DEVICE')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if CUDA is available and return the appropriate device.
def get_device():
    if torch.cuda.is_available():
        logger.info("CUDA is available. Using GPU.")
        return "cuda"
    else:
        logger.error("CUDA is not available. Using CPU. This may lead to inefficient performance.")
        return "cpu"

device = get_device()

logger.info("Initializing Stable Diffusion Pipelines")

# Load the Stable Diffusion XL model
model_id = "SG161222/RealVisXL_V4.0"
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
pipe = pipe.to(device)

# Load the ControlNet model and local image
controlnet_model_id = "thibaud/controlnet-openpose-sdxl-1.0"
controlnet = ControlNetModel.from_pretrained(controlnet_model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
controlnet = controlnet.to(device)
control_image = Image.open("portrait.png")

def custom_progress_callback(step: int, t: int, latents, total_steps: int):
    progress = (step + 1) / total_steps * 100
    logger.info(f"Progress: Step {step + 1}/{total_steps} ({progress:.2f}%)")

# Generate random seeds for stable diffusion
def generate_random_seed():
    return random.randint(0, 2**32 - 1)

def create_execution_info(start_time: float):
    elapsed_time = time.time() - start_time
    return {"ms": elapsed_time, "device": DEVICE}

# Process task of supabase queue
def process_task(task):
    task_id = task['id']
    task_data = task.get("request", {})
    logger.info(f"Processing task ID: {task_id} with data: {task_data}")

    start_time = time.time()

    try:
        supabase.from_('job_queue').update({'status': 'running'}).eq('id', task_id).execute()
        generation_response = generate_image(task_data)
        execution_info = create_execution_info(start_time)
        supabase.from_('job_queue').update({'status': 'succeeded', "response": generation_response, "execution_info": execution_info}).eq('id', task_id).execute()
        logger.info(f"Task {task_id} processed in {execution_info.ms:.2f} seconds, with response: {generation_response}")
    except Exception as e:
        logger.exception(f"Error processing task ID: {task_id}, error: {e}")
        supabase.from_('job_queue').update({'status': 'failed', "execution_info": create_execution_info(start_time)}).eq('id', task_id).execute()

# Generate image for specific input data
def generate_image(data):
    if not data:
        logger.error("Data object for image generation is required")
        raise ValueError("Data object for image generation is required")

    prompt = data.get('prompt', None)
    negative_prompt = data.get('negative_prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    num_inference_steps = data.get('num_inference_steps', 20)
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

    logger.info(f"Using seed: {seed}")

    with torch.no_grad():
        generator = torch.manual_seed(seed)
        try:
            total_steps = num_inference_steps
            with tqdm(total=total_steps, desc="Generating Image") as pbar:
                def progress_callback(step, t, latents, pbar, total_steps):
                    custom_progress_callback(step, t, latents, total_steps)
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
                        callback=lambda step, t, latents: progress_callback(step, t, latents, pbar, total_steps),
                        callback_steps=5
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
                        callback=lambda step, t, latents: progress_callback(step, t, latents, pbar, total_steps),
                        callback_steps=5
                    ).images[0]
        except Exception as e:
            logger.exception("Error during image generation")
            raise e

        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

        # Upload image to Supabase storage
        try:
            filename = get_filename()
            supabase.storage.from_("models").upload(path=f"{filename}.png", file=img_io.read(), file_options={"content-type": "image/png"})
        except Exception as e:
            logger.error(f"Failed to upload image to Supabase storage with error: {e}")
            raise ValueError("Failed to upload image to Supabase storage")

    return {"assets": [{"image": filename, "seed": seed}]}

def get_filename():
    return f"{uuid.uuid4()}"

# Subscribe to supabase job queue
def subscribe_to_queue():
    logger.info(f"Connecting to Supabase with ID {SUPABASE_ID}")
    def on_insert(payload):
        new_task = payload["record"]
        if new_task['status'] == 'queued':
            process_task(new_task)

    try:
        url = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
        s = Socket(url)
        s.connect()

        channel_1 = s.set_channel("realtime:public:job_queue")
        channel_1.join().on("INSERT", on_insert)
        s.listen()
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {e}")
        raise ValueError("Error connecting to Supabase")


if __name__ == '__main__':
    subscribe_to_queue()
  #  app.run(host='0.0.0.0', port=8080)

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