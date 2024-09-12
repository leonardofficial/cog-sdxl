from io import BytesIO
from helpers.filename import get_filename
from helpers.logger import logger
from supabase_helpers.supabase_manager import get_supabase


# Upload image to Supabase storage
def upload_image(bucket: str, data: BytesIO):
    filename = get_filename()

    try:
        supabase = get_supabase()
        supabase.storage.from_(bucket).upload(path=f"{filename}.png", file=data, file_options={"content-type": "image/png"})
        return filename
    except Exception as e:
        logger.exception("Failed to upload image to supabase: ", e)
        raise e