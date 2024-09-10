from helpers.seed import generate_random_seed
from data_types.types import TextToImageInput
from stable_diffusion.stable_diffusion_manager import stableDiffusionManager
from supabase_helpers.storage import upload_image

def text_to_image(data: TextToImageInput):
    if not data:
        raise ValueError("Data input for text-to-image is required")

    if not data.prompt:
        raise ValueError("Prompt for text-to-image is required")

    images = []
    for i in range(data.num_options if data.seed is None else 1): # If seed is provided, only generate one image
        current_seed = data.seed if data.seed is not None else generate_random_seed()

        image = stableDiffusionManager.text_to_image(data, seed=current_seed)
        filename = upload_image("images", image)
        images.append({"image": f"{filename}.png", "seed": current_seed})


    return {"assets": images}