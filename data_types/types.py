import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any

@dataclass
class ImagePluginType:
    id: str
    weight: int
    data: Optional[Any] = None

    def json(self):
        data_dict = asdict(self)
        return json.dumps(data_dict, default=str)

    @classmethod
    def from_json(cls, data: dict):
        return cls(
            id=data['id'],
            weight=data['weight'],
            data=data.get('data')
        )

@dataclass
class TextToImageRequestType:
    type: str
    prompt: str
    num_options: int = 1
    height: int = 1024
    width: int = 1024
    plugins: Optional[List[ImagePluginType]] = field(default_factory=list)
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None

    def json(self):
        data_dict = asdict(self)
        if self.plugins:
            data_dict['plugins'] = [json.loads(plugin.json()) for plugin in self.plugins]
        return json.dumps(data_dict, default=str)

    @classmethod
    def from_json(cls, data: dict):
        plugins = [ImagePluginType.from_json(plugin) for plugin in data.get('plugins', [])]
        return cls(
            type=data.get('type'),
            prompt=data['prompt'],
            num_options=data.get('num_options', 1),
            height=data.get('height', 1024),
            width=data.get('width', 1024),
            plugins=plugins,
            negative_prompt=data.get('negative_prompt'),
            seed=data.get('seed')
        )

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

    @classmethod
    def from_json(cls, data: dict):
        request = TextToImageRequestType.from_json(data['request'])
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        return cls(
            id=data['id'],
            request=request,
            status=data['status'],
            created_at=created_at,
            execution_info=data.get('execution_info'),
            response=data.get('response')
        )

@dataclass
class StableDiffusionExecutionType:
    image: bytes
    seed: str
    runtime: int

    def json(self):
        data_dict = asdict(self)
        return json.dumps(data_dict, default=str)

    @classmethod
    def from_json(cls, data: dict):
        return cls(
            image=data['image'],
            seed=data['seed'],
            runtime=data['runtime']
        )

class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STOPPED = "stopped"
    ASSIGNED = "assigned"