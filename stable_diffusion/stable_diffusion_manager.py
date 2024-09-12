import logging
from datetime import time, datetime
from io import BytesIO
from typing import Any, List

import torch
from tqdm import tqdm

from data_types.types import TextToImageRequestType, StableDiffusionExecutionType
from helpers.logger import logger, TqdmToLogger
from config.consts import stable_diffusion_model_id, stable_diffusion_inference_steps, stable_diffusion_cfg
from diffusers import DiffusionPipeline
from helpers.cuda import get_device


class StableDiffusionManager:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.pipeline = None
        #self.plugins: List[LoraPlugin] = []
        self.download_weights()  # Download weights before anything else

    # Download weights for the Stable Diffusion model
    def download_weights(self):
        device = get_device()
        logger.info("Downloading Stable Diffusion model weights...")
        try:
            self.pipeline = DiffusionPipeline.from_pretrained(
                stable_diffusion_model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                cache_dir="./model_cache",
                force_download=False,  # Avoid forcing a re-download
                local_files_only=False,  # Download from the hub if not found locally
            )

            self.pipeline = self.pipeline.to(device)  # Move to specified device

            # Disable progress bar
            self.pipeline.set_progress_bar_config(disable=True)
            logger.info("Model weights downloaded successfully.")
        except Exception as e:
            logger.exception("Error during model weight download")
            raise e

    # Apply all registered plugins to the pipeline.
    def initialize_plugins(self):
        logger.info("Initializing plugins...")

    def text_to_image(self, data: TextToImageRequestType, **kwargs) -> StableDiffusionExecutionType:
        logger.info("Generating image with data: %s", data)

        start_time = datetime.now()
        with torch.no_grad():
            generator = torch.manual_seed(data.seed)
            try:
                inference_steps = stable_diffusion_inference_steps
                tqdm_out = TqdmToLogger(logger, level=logging.INFO)
                with tqdm(total=inference_steps, desc="Image generation", file=tqdm_out) as pbar:
                    def progress_callback(pipeline, i, t, callback_kwargs):
                        pbar.update(1)

                    image = self.pipeline(
                        data.prompt,
                        negative_prompt=data.negative_prompt,
                        guidance_scale=stable_diffusion_cfg,
                        generator=generator,
                        height=data.height,
                        width=data.width,
                        num_inference_steps=inference_steps,
                        callback_on_step_end=progress_callback,
                        loras=data.plugins
                    ).images[0]
            except Exception as e:
                logger.exception("Error during image generation")
                raise e

            img_io = BytesIO()
            image.save(img_io, 'PNG')
            img_io.seek(0)

            runtime = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Completed Text-To-Image Request in {runtime} seconds")

            return StableDiffusionExecutionType(image=img_io, runtime=runtime)

    # Retrieve the current Stable Diffusion pipeline.
    def get_pipeline(self) -> DiffusionPipeline:
        if self.pipeline is None:
            raise RuntimeError("Stable Diffusion pipeline not initialized.")
        return self.pipeline

    # Reset the pipeline by reinitializing it and applying plugins.
    def reset_pipeline(self):
        self.initialize_pipeline()


_stableDiffusionManager: StableDiffusionManager = None

def get_stable_diffusion() -> StableDiffusionManager:
    global _stableDiffusionManager
    if _stableDiffusionManager is None:
        _stableDiffusionManager = StableDiffusionManager("Stable Diffusion")
    return _stableDiffusionManager