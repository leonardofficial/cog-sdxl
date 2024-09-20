import logging
import os
from datetime import datetime
from io import BytesIO
from typing import List, Dict
import torch
from tqdm import tqdm
from data_types.types import TextToImageRequestType, StableDiffusionExecutionType, ImagePluginType
from helpers.logger import logger, TqdmToLogger
from config.consts import stable_diffusion_model_id, stable_diffusion_inference_steps, stable_diffusion_cfg
from diffusers import DiffusionPipeline
from helpers.cuda import get_device
from supabase_helpers.supabase_plugins import get_plugins_from_supabase
from supabase_helpers.supabase_storage import download_file_from_supabase_bucket

lora_cache_dir = "./lora_cache"
model_cache_dir = "./model_cache"

class StableDiffusionManager:
    def __init__(self, model_name: str):
        logger.info(f"Initializing Stable Diffusion with: {model_name}")
        self.model_name = model_name
        self.pipeline = None
        self.plugin_cache: Dict[str, str] = {}  # Maps LoRA identifiers to local file paths
        self.download_weights()
        self.download_plugins()
        logger.info("Stable Diffusion is ready.")

    # Download weights for the Stable Diffusion model
    def download_weights(self):
        device = get_device()
        logger.info("Downloading Stable Diffusion model weights...")
        try:
            self.pipeline = DiffusionPipeline.from_pretrained(
                stable_diffusion_model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                cache_dir=model_cache_dir,
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

    def download_plugins(self):
        logger.info("Downloading Plugin (LoRA) weights...")
        os.makedirs(lora_cache_dir, exist_ok=True)

        plugin_ids = get_plugins_from_supabase()

        for plugin_id in plugin_ids:
            filename = f"{plugin_id}.safetensors"
            local_lora_path = os.path.join(
                lora_cache_dir, filename.replace("/", "_")
            )
            if not os.path.exists(local_lora_path):
                logger.info(f"Downloading Plugin (LoRA): {filename}")
                try:
                    downloaded_file = download_file_from_supabase_bucket("plugin_weights", f"{filename}")
                    with open(local_lora_path, "wb") as f:
                        f.write(downloaded_file)

                    self.plugin_cache[plugin_id] = local_lora_path
                except Exception as e:
                    logger.exception(f"Failed to download LoRA: {filename}")
            else:
                logger.info(f"LoRA already downloaded: {filename}")
                self.plugin_cache[plugin_id] = local_lora_path

        logger.info("Plugin (LoRA) weights downloaded successfully.")

    def load_plugins_to_memory(self, plugins: tuple[ImagePluginType]): # type needs to be tuple to allow cache to hash function call
        for plugin in plugins:
            self.load_plugin_to_memory(plugin)

    def load_plugin_to_memory(self, plugin: ImagePluginType):
        logger.debug(f"Loading Plugin (LoRA) weight into memory: {plugin.id}")
        lora_path = self.plugin_cache.get(plugin.id)
        if not lora_path:
            logger.error(f"Plugin (LoRA) not found in cache: {plugin.id}")
            raise FileNotFoundError(f"Plugin (LoRA) not found: {plugin.id}")
        self.pipeline.load_lora_weights(lora_path)

    def offload_plugins_from_memory(self):
        logger.debug("Unloading Plugin (LoRA) weights")
        self.pipeline.unload_lora_weights()

    def add_plugins_to_prompt(self, data: TextToImageRequestType):
        if (data.plugins):
            for plugin in data.plugins:
                data.prompt += f", <{plugin.id}:{plugin.weight}>"

        return data


    def text_to_image(self, data: TextToImageRequestType, **kwargs) -> StableDiffusionExecutionType:
        logger.info("Generating image with data: %s", data)

        start_time = datetime.now()
        with torch.no_grad():
            generator = torch.manual_seed(data.seed)
            try:
                inference_steps = stable_diffusion_inference_steps
                tqdm_out = TqdmToLogger(logger, level=logging.INFO)

                # load plugins
                if data.plugins:
                    self.load_plugins_to_memory(tuple(data.plugins))

                data = self.add_plugins_to_prompt(data)
                print(data.prompt)

                with tqdm(total=inference_steps, desc="text-to-image", file=tqdm_out) as pbar:
                    def progress_callback(step, t, latents):
                        pbar.update(1)

                    # generate image
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
                logger.error("Error during image generation: %s", e)
                raise e
            finally:
                if data.plugins:
                    self.offload_plugins_from_memory()

            img_io = BytesIO()
            image.save(img_io, 'PNG')
            img_io.seek(0)

            runtime = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Completed Text-To-Image Request in {runtime/1000} seconds")

            return StableDiffusionExecutionType(image=img_io.read(), runtime=runtime, seed=data.seed)



    # Retrieve the current Stable Diffusion pipeline.
    def get_pipeline(self) -> DiffusionPipeline:
        if self.pipeline is None:
            raise RuntimeError("Stable Diffusion pipeline not initialized.")
        return self.pipeline


_stableDiffusionManager: StableDiffusionManager = None

def get_stable_diffusion() -> StableDiffusionManager:
    global _stableDiffusionManager
    if _stableDiffusionManager is None:
        _stableDiffusionManager = StableDiffusionManager("Stable Diffusion")
    return _stableDiffusionManager