from numpy.f2py.auxfuncs import throw_error
from pydantic import ValidationError
from data_types.types_validation import TextToImageRequestModel
from helpers.seed import generate_random_seed
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from data_types.types import TextToImageRequestType, StableDiffusionExecutionType

def text_to_image(request: TextToImageRequestType) -> list[StableDiffusionExecutionType]:
    if request is None:
        throw_error("request data is missing")

    try:
        TextToImageRequestModel(**request.__dict__)
    except ValidationError as e:
        throw_error(f"invalid request data: {e.errors()}")

    images = []
    stable_diffusion = get_stable_diffusion()

    # Only generate one image, if seed is provided
    num_iterations = request.num_options if request.seed is None else 1
    for _ in range(num_iterations):
        try:
            current_seed = request.seed if request.seed is not None else generate_random_seed()
            request.seed = current_seed

            # Generate image with stable diffusion
            response = stable_diffusion.text_to_image(request)
            images.append(response)

        except Exception as e:
            throw_error(f"image generation failed")

    return images