from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ImagePluginType:
    id: str
    weight: int
    data: Optional[Any] = None

@dataclass
class TextToImageRequestType:
    prompt: str
    num_options: int = 1
    height: int = 1024
    width: int = 1024
    plugins: Optional[List[ImagePluginType]] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

@dataclass
class SupabaseJobQueueType:
    id: str
    request: TextToImageRequestType
    status: str
    created_at: str
    execution_info: Optional[Any] = None
    response: Optional[Any] = None