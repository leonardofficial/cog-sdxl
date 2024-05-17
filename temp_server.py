from flask import Flask, request, send_file, jsonify
from io import BytesIO
import torch
from diffusers import DiffusionPipeline
import random
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_device():
    """
    Check if CUDA is available and return the appropriate device.
    """
    if torch.cuda.is_available():
        logger.info("CUDA is available. Using GPU.")
        return "cuda"
    else:
        logger.error("CUDA is not available. Using CPU.")
        return "cpu"

# Execute the device detection at the beginning
device = get_device()

# Load the Stable Diffusion XL model
model_id = "SG161222/RealVisXL_V4.0"
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
pipe = pipe.to(device)

def custom_progress_callback(step: int, t: int, latents):
    logger.info(f"Step {step + 1} of {t}")

def generate_random_seed():
    return random.randint(0, 2**32 - 1)

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json

    prompt = data.get('prompt', None)
    negative_prompt = data.get('negative_prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    num_inference_steps = data.get('num_inference_steps', 50)
    seed = data.get('seed', generate_random_seed())

    if not prompt:
        logger.error("Prompt is required")
        return jsonify({"error": "Prompt is required"}), 400

    with torch.no_grad():
        generator = torch.manual_seed(seed)
        try:
            image = pipe(
                prompt,
                negative_prompt=negative_prompt,
                guidance_scale=cfg,
                generator=generator,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                callback=custom_progress_callback,
                callback_steps=1  # Ensure the callback is called at each step
            ).images[0]
        except Exception as e:
            logger.exception("Error during image generation")
            return jsonify({"error": str(e)}), 500

        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

    logger.info("Image generated successfully")
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
