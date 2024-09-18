import json
from data_types.types import StableDiffusionExecutionType
from supabase_helpers.supabase_connection import get_supabase_postgres
from supabase_helpers.supabase_storage import upload_files_to_supabase_bucket


def create_supabase_image_entities(executions: list[StableDiffusionExecutionType], job_id: str):
    if not job_id:
        raise ValueError("job_id is required")

    try:
        images_data = [execution.image for execution in executions]
        filenames = upload_files_to_supabase_bucket("images", images_data)
    except Exception:
        raise Exception("image upload to bucket failed")

    supabase = get_supabase_postgres()
    try:
        cursor = supabase.cursor()

        # Prepare data for batch insertion
        insert_values = []
        for filename, execution in zip(filenames, executions):
            data = {
                "filename": filename,
                "seed": execution.seed,
                "runtime": execution.runtime
            }
            insert_values.append((json.dumps(data), False, str(job_id)))

        # Build the INSERT query for multiple rows
        args_str = ','.join(cursor.mogrify("(%s, %s, %s)", x).decode('utf-8') for x in insert_values)
        cursor.execute("INSERT INTO images (data, is_public, job_id) VALUES " + args_str + ";")

        supabase.commit()
    except Exception as e:
        supabase.rollback()
        raise e