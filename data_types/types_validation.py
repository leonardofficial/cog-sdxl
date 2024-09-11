from typing import Optional
from pydantic import BaseModel, Field, field_validator

class TextToImageRequestModel(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt for generating images")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt for generating images")
    num_options: int = Field(1, gt=0, description="Number of image options to generate")
    height: int = Field(1024, gt=0, description="Height of the generated image")
    width: int = Field(1024, gt=0, description="Width of the generated image")
    seed: Optional[int] = None

    @field_validator('prompt')
    def validate_prompt(self, value):
        if len(value.strip()) == 0:
            raise ValueError("Prompt cannot be empty")
        return value


class SupabaseJobQueueType(BaseModel):
    id: str = Field(..., description="job id")
    request: TextToImageRequestModel = Field(..., description="request data (e.g. for generating images)")
    status: str = Field(..., description="current status of the job")
    created_at: str = Field(..., description="timestamp when the job was created by user")

    @field_validator('request')
    def validate_request(self, value):
        TextToImageRequestModel(**value)
        return value