from helpers.seed import generate_random_seed

from data_types.types import TextToImageRequestType, StableDiffusionExecutionType
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from supabase_helpers.supabase_storage import upload_image_to_supabase_bucket


def text_to_portrait(data: TextToImageRequestType) -> list[StableDiffusionExecutionType]:
    if not data:
        raise ValueError("Data input for text-to-portrait is required")

    if not data.prompt:
        raise ValueError("Prompt for text-to-portrait is required")

    images = []
    stable_diffusion = get_stable_diffusion()
    for i in range(4):
        current_seed = generate_random_seed()

        response = stable_diffusion.text_to_image(data, seed=current_seed)
        filename = upload_image_to_supabase_bucket("personas", response.image)
        images.append({"image": f"{filename}.png", "seed": current_seed})


    return {"assets": images}