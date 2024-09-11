from helpers.seed import generate_random_seed

from data_types.types import TextToImageRequestType
from stable_diffusion.stable_diffusion_manager import stableDiffusionManager
from supabase_helpers.storage import upload_image


def text_to_portrait(data: TextToImageRequestType):
    if not data:
        raise ValueError("Data input for text-to-portrait is required")

    if not data.prompt:
        raise ValueError("Prompt for text-to-portrait is required")

    images = []
    for i in range(4):
        current_seed = generate_random_seed()

        image = stableDiffusionManager.text_to_image(data, seed=current_seed)
        filename = upload_image("personas", image)
        images.append({"image": f"{filename}.png", "seed": current_seed})


    return {"assets": images}