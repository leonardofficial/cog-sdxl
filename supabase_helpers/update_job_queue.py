import json

from data_types.types import JobStatus
from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase_postgres

# Update the status of a job in the job_queue table.
def update_job_queue(job_id, job_status: JobStatus, response_data=None, execution_metadata_update=None):
    conn = get_supabase_postgres()
    cursor = conn.cursor()

    try:
        sql = """
            UPDATE job_queue
            SET status = %s
        """
        params = [job_status.value]

        if execution_metadata_update is not None:
            execution_metadata_update_json = json.dumps(execution_metadata_update)
            sql += ", execution_metadata = %s"
            params.append(execution_metadata_update_json)

        if response_data is not None:
            response_json = json.dumps(response_data)
            sql += ", response_data = %s"
            params.append(response_json)

        sql += " WHERE id = %s;"
        params.append(job_id)

        cursor.execute(sql, tuple(params))
        logger.info(f"Updated job {job_id} status to {job_status.value}.")
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")
    finally:
        cursor.close()