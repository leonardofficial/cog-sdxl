from flask import Flask, request, send_file
from io import BytesIO
import torch
from diffusers import DiffusionPipeline

app = Flask(__name__)

# Check if CUDA is available and set device accordingly
if torch.cuda.is_available():
    device = "cuda"
    print("CUDA is available. Using GPU.")
else:
    device = "cpu"
    print("CUDA is not available. Using CPU.")

# Load the Stable Diffusion XL model
model_id = "SG161222/RealVisXL_V4.0"
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
pipe = pipe.to(device)

def custom_progress_callback(step: int, total_steps: int):
    print(f"Step {step + 1} of {total_steps}")

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json

    prompt = data.get('prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 1024)
    height = data.get('height', 1024)

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    with torch.no_grad():
        generator = torch.manual_seed(42)
        image = pipe(prompt, guidance_scale=cfg, generator=generator, height=height, width=width, callback=custom_progress_callback).images[0]
        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
