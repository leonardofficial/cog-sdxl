import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any

class JobType(Enum):
    TEXT_TO_IMAGE = "text-to-image"
    TEXT_TO_PORTRAIT = "text-to-portrait"

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
    job_type: JobType
    request_data: TextToImageRequestType
    job_status: str
    created_at: datetime
    execution_metadata: Optional[Any] = None

    def json(self):
        data_dict = asdict(self)
        data_dict['created_at'] = self.created_at.isoformat() if self.created_at else None
        data_dict['request_data'] = json.loads(self.request_data.json())
        data_dict['job_type'] = self.job_type.value
        return json.dumps(data_dict, default=str)

    @classmethod
    def from_json(cls, data: dict):
        request_data = TextToImageRequestType.from_json(data['request_data'])
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        return cls(
            id=data['id'],
            job_type=JobType(data['job_type']),
            request_data=request_data,
            job_status=data['job_status'],
            created_at=created_at,
            execution_metadata=data.get('execution_metadata')
        )

@dataclass
class StableDiffusionExecutionType:
    image: bytes
    seed: int
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

