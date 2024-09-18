from pydantic import ValidationError
from data_types.types_validation import TextToImageRequestModel
from helpers.seed import generate_random_seed
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from data_types.types import TextToImageRequestType, StableDiffusionExecutionType

def text_to_image(request: TextToImageRequestType) -> list[StableDiffusionExecutionType]:
    if request is None:
        raise Exception("request data is missing")

    try:
        TextToImageRequestModel(**request.__dict__)
    except ValidationError as e:
        raise Exception(f"invalid request data: {e.errors()}")

    images = []
    stable_diffusion = get_stable_diffusion()

    for _ in range(request.num_options):
        current_seed = request.seed if request.seed is not None else generate_random_seed()
        request.seed = current_seed

        # Generate image with stable diffusion
        response = stable_diffusion.text_to_image(request)
        images.append(response)

    return images