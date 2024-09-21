from pydantic import ValidationError
from data_types.types_validation import TextToImageRequestModel
from helpers.seed import generate_random_seed
from moderate.sanitize_prompt import sanitize_prompt
from stable_diffusion.stable_diffusion_manager import get_stable_diffusion
from data_types.types import TextToImageRequestType, StableDiffusionExecutionType, SupabaseJobQueueType
from supabase_helpers.supabase_team import team_nsfw_allowed

def text_to_image(request: SupabaseJobQueueType) -> list[StableDiffusionExecutionType]:
    # Validate Input
    request_data = request.request_data
    if request_data is None:
        raise Exception("request data is missing")

    try:
        TextToImageRequestModel(**request_data.__dict__)
    except ValidationError as e:
        raise Exception(f"invalid request data: {e.errors()}")

    # Moderate Input
    nsfw_allowed = team_nsfw_allowed(request.team)
    sanitize_prompt(request_data.prompt, nsfw_allowed=nsfw_allowed)

    # Generate Image(s)
    images = []
    stable_diffusion = get_stable_diffusion()
    for _ in range(request_data.num_options):
        # Generate image with stable diffusion
        response = stable_diffusion.text_to_image(request_data)
        images.append(response)

    return images