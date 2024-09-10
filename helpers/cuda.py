import torch
from helpers.logger import logger

def get_device():
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA detected. Using GPU: {gpu_name}")
        return "cuda"
    else:
        logger.error("CUDA not detected. Using CPU instead. This may lead to inefficient performance.")
        return "cpu"