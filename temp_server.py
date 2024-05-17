from flask import Flask, request, send_file, jsonify
from io import BytesIO
import torch
from diffusers import DiffusionPipeline
import random
import logging
import time
import json
from tqdm import tqdm

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

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

def custom_progress_callback(step: int, t: int, latents):
    progress = (step + 1) / t * 100
    progress_bar = f"{progress:.2f}%"
    tqdm.write(f"{progress_bar} - {time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Progress: Step {step + 1} ({progress:.2f}%)")

def generate_random_seed():
    return random.randint(0, 2**32 - 1)

@app.route('/generate', methods=['POST'])
def generate_image():
    start_time = time.time()
    data = request.json

    prompt = data.get('prompt', None)
    negative_prompt = data.get('negative_prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    num_inference_steps = data.get('num_inference_steps', 50)
    seed = data.get('seed', generate_random_seed())

    request_parameters = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "cfg": cfg,
        "width": width,
        "height": height,
        "num_inference_steps": num_inference_steps,
        "seed": seed
    }
    logger.info(f"Request with parameters: {json.dumps(request_parameters)}")

    if not prompt:
        logger.error("Prompt is required")
        return jsonify({"error": "Prompt is required"}), 400

    with torch.no_grad():
        generator = torch.manual_seed(seed)
        try:
            with tqdm(total=num_inference_steps, desc="Generating", unit="step") as pbar:
                def progress_callback(step, t, latents):
                    custom_progress_callback(step, t, latents)
                    pbar.update(1)

                image = pipe(
                    prompt,
                    negative_prompt=negative_prompt,
                    guidance_scale=cfg,
                    generator=generator,
                    height=height,
                    width=width,
                    num_inference_steps=num_inference_steps,
                    callback_on_step_end=progress_callback,
                    callback_steps=1  # Ensure the callback is called at each step
                ).images[0]
        except Exception as e:
            logger.exception("Error during image generation")
            return jsonify({"error": str(e)}), 500

        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

    elapsed_time = time.time() - start_time
    logger.info(f"Image generated successfully in {elapsed_time:.2f} seconds")
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
