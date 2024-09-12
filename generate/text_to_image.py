from pydantic import ValidationError
from data_types.types_validation import TextToImageRequestModel
from helpers.logger import logger
from helpers.seed import generate_random_seed
from data_types.types import TextToImageRequestType
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from supabase_helpers.storage import upload_image

def text_to_image(request: TextToImageRequestType):
    if request is None:
        return {"error": "request data is missing"}

    # Validate request data
    try:
        TextToImageRequestModel(**request.__dict__)
    except ValidationError as e:
        return {"error": f"invalid request data: {e.errors()}"}

    images = []
    stable_diffusion = get_stable_diffusion()
    try:
        for i in range(request.num_options if request.seed is None else 1):
            # [1/2] Generate image
            try:
                current_seed = request.seed if request.seed is not None else generate_random_seed()
                image = stable_diffusion.text_to_image(request, seed=current_seed)
            except Exception as image_generation_error:
                logger.error(f"Error generating image: {image_generation_error}")
                return {"error": "Image generation failed", "details": str(image_generation_error)}

            # [2/2] Upload image to bucket
            try:
                filename = upload_image("images", image)
            except Exception as upload_error:
                logger.error(f"Error uploading image: {upload_error}")
                return {"error": "Image upload failed", "details": str(upload_error)}

            images.append({"image": f"{filename}.png", "seed": current_seed})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "An unexpected error occurred", "details": str(e)}

    return {"assets": images}