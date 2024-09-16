import time
from helpers.load_config import load_config
config = load_config()

def create_execution_info(start_time: float):
    elapsed_time = time.time() - start_time
    return {"ms": elapsed_time * 1000, "gpu": config.NODE_GPU, "node_id": config.NODE_ID}