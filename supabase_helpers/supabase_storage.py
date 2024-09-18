from helpers.filename import get_filename
from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase

def upload_image_to_supabase_bucket(bucket: str, data: bytes) -> str:
    filename = get_filename()

    try:
        supabase = get_supabase()
        supabase.storage.from_(bucket).upload(path=f"{filename}.png", file=data, file_options={"content-type": "image/png"})
        return filename
    except Exception as e:
        logger.exception("Failed to upload image to supabase: ", e)
        raise e

def upload_images_to_supabase_bucket(bucket: str, files: list[bytes]) -> list[str]:
    filenames = []
    for file in files:
        filename = upload_image_to_supabase_bucket(bucket, file)
        filenames.append(filename)

    return filenames

def download_file_from_supabase_bucket(bucket: str, filename: str):
    try:
        supabase = get_supabase()
        response = supabase.storage.from_(bucket).download(path=filename)
        return response.data
    except Exception as e:
        logger.exception("Failed to download image from supabase: ", e)
        raise e