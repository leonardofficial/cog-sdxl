from flask import Flask, request, jsonify, send_file
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


@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json

    prompt = data.get('prompt', None)
    cfg = data.get('cfg', 7.5)
    width = data.get('width', 512)
    height = data.get('height', 512)
    num_images = data.get('num_images', 1)

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    if not isinstance(num_images, int) or num_images < 1:
        return jsonify({"error": "num_images must be a positive integer"}), 400

    images = []
    with torch.no_grad():
        for _ in range(num_images):
            generator = torch.manual_seed(42)
            image = pipe(prompt, guidance_scale=cfg, generator=generator, height=height, width=width).images[0]
            img_io = BytesIO()
            image.save(img_io, 'PNG')
            img_io.seek(0)
            images.append(img_io.getvalue())

    return jsonify({"images": [img.decode('latin1') for img in images]})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
