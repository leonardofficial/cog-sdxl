from io import BytesIO
from helpers.filename import get_filename
from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase


# Upload image to Supabase storage
def upload_image(bucket: str, data: bytes) -> str:
    filename = get_filename()

    try:
        supabase = get_supabase()
        supabase.storage.from_(bucket).upload(path=f"{filename}.png", file=data, file_options={"content-type": "image/png"})
        return filename
    except Exception as e:
        logger.exception("Failed to upload image to supabase: ", e)
        raise e

def upload_images(bucket: str, files: list[bytes]) -> list[str]:
    filenames = []
    for file in files:
        filename = upload_image(bucket, file)
        filenames.append(filename)

    return filenames