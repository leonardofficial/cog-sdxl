from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ImagePlugin:
    id: str
    weight: int
    data: Any = None

@dataclass
class TextToImageInput:
    prompt: str
    num_options: int = 1
    height: int = 1024
    width: int = 1024
    plugins: List[ImagePlugin] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None