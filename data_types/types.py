import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Any

@dataclass
class ImagePluginType:
    id: str
    weight: int
    data: Optional[Any] = None

    def json(self):
        data_dict = asdict(self)
        return json.dumps(data_dict, default=str)

@dataclass
class TextToImageRequestType:
    prompt: str
    num_options: int = 1
    height: int = 1024
    width: int = 1024
    plugins: Optional[List[ImagePluginType]] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

    def json(self):
        data_dict = asdict(self)
        if self.plugins:
            data_dict['plugins'] = [plugin.json() for plugin in self.plugins]
        return json.dumps(data_dict, default=str)

@dataclass
class SupabaseJobQueueType:
    id: str
    request: TextToImageRequestType
    status: str
    created_at: datetime
    execution_info: Optional[Any] = None
    response: Optional[Any] = None

    def json(self):
        data_dict = asdict(self)
        data_dict['created_at'] = self.created_at.isoformat() if self.created_at else None
        data_dict['request'] = json.loads(self.request.json())
        return json.dumps(data_dict, default=str)