import logging
from io import BytesIO
from typing import Any, List

import torch
from tqdm import tqdm

from data_types.types import TextToImageRequestType
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
            progress_bar = tqdm(desc="Downloading model weights", unit="B", unit_scale=True, file=TqdmToLogger(logger, level=logging.INFO))

            def progress_callback(current, total):
                progress_bar.total = total
                progress_bar.n = current
                progress_bar.refresh()

            DiffusionPipeline.from_pretrained(
                stable_diffusion_model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                cache_dir="./model_cache",
                resume_download=True,  # Resume partially downloaded files
                force_download=False,  # Avoid forcing a re-download
                local_files_only=False,  # Download from the hub if not found locally
                progress_callback=progress_callback,  # Custom progress callback
            )

            progress_bar.close()
            self.pipeline = self.pipeline.to(device)  # Move to specified device
            # self.initialize_plugins()
            logger.info("Model weights downloaded successfully.")
        except Exception as e:
            logger.exception("Error during model weight download")
            raise e

    # Apply all registered plugins to the pipeline.
    def initialize_plugins(self):
        logger.info("Initializing plugins...")

    def text_to_image(self, data: TextToImageRequestType, **kwargs) -> Any:
        logger.info("Generating image with data: %s", data)
        with torch.no_grad():
            generator = torch.manual_seed(data.seed)
            try:
                inference_steps = stable_diffusion_inference_steps
                tqdm_out = TqdmToLogger(logger, level=logging.INFO)
                with tqdm(total=inference_steps, desc="Image generation", file=tqdm_out) as pbar:
                    def progress_callback(step, t, latents):
                        pbar.update(1)

                    logger.info("Generating image without ControlNet")
                    image = self.pipeline(
                        data.prompt,
                        negative_prompt=data.negative_prompt,
                        guidance_scale=stable_diffusion_cfg,
                        generator=generator,
                        height=data.height,
                        width=data.width,
                        num_inference_steps=inference_steps,
                        callback=progress_callback,
                        callback_steps=1,
                        loras=data.plugins
                    ).images[0]
            except Exception as e:
                logger.exception("Error during image generation")
                raise e

            img_io = BytesIO()
            image.save(img_io, 'PNG')
            img_io.seek(0)

            return img_io

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