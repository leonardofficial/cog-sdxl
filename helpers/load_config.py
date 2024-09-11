from pydantic import ValidationError, Field
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    SUPABASE_ID: str = Field(..., alias='SUPABASE_ID')  # Required
    SUPABASE_URL: str = Field(..., alias='SUPABASE_URL')  # Required
    SUPABASE_KEY: str = Field(..., alias='SUPABASE_KEY')  # Required

    SUPABASE_POSTGRES_USER: str = Field(..., alias='SUPABASE_POSTGRES_USER')  # Required
    SUPABASE_POSTGRES_PASSWORD: str = Field(..., alias='SUPABASE_POSTGRES_PASSWORD')  # Required
    SUPABASE_POSTGRES_DB: str = Field(..., alias='SUPABASE_POSTGRES_DB')  # Required
    SUPABASE_POSTGRES_HOST: str = Field(..., alias='SUPABASE_POSTGRES_HOST')  # Required
    SUPABASE_POSTGRES_PORT: int = Field(..., alias='SUPABASE_POSTGRES_PORT')  # Required

    RABBITMQ_HOST: str = Field(..., alias='RABBITMQ_HOST')  # Required
    RABBITMQ_QUEUE: str = Field(..., alias='RABBITMQ_QUEUE')  # Required
    RABBITMQ_QUEUE_SIZE: int = Field(..., alias='RABBITMQ_QUEUE_SIZE')  # Required
    RABBITMQ_DEFAULT_USER: str = Field(..., alias='RABBITMQ_DEFAULT_USER')  # Required
    RABBITMQ_DEFAULT_PASS: str = Field(..., alias='RABBITMQ_DEFAULT_PASS')  # Required
    RABBITMQ_DEFAULT_VHOST: str = Field(..., alias='RABBITMQ_DEFAULT_VHOST')

    JOB_DISCARD_THRESHOLD: int = Field(1440, alias='JOB_DISCARD_THRESHOLD')  # Required

    NODE_GPU: str = Field(..., alias='NODE_GPU')  # Required
    NODE_ID: str = Field(..., alias='NODE_ID')  # Required


    class Config:
        env_file = '.env'  # Optionally load variables from a .env file

# Singleton to ensure config is loaded once
_config = None

def load_config() -> Config:
    global _config
    if _config is None:
        try:
            _config = Config()
        except ValidationError as e:
            print("Configuration Error:", e.json())
            raise SystemExit("Exiting due to invalid configuration.")
    return _config
