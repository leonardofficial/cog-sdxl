import json

from data_types.types import JobStatus
from helpers.logger import logger
from supabase_helpers.supabase_connection import get_supabase_postgres

# Update the status of a job in the job_queue table.
def update_job_queue(job_id, status: JobStatus, response=None, execution_info_update=None):
    conn = get_supabase_postgres()
    cursor = conn.cursor()

    try:
        sql = """
            UPDATE job_queue
            SET status = %s
        """
        params = [status.value]

        if execution_info_update is not None:
            execution_info_update_json = json.dumps(execution_info_update)
            sql += ", execution_info = %s"
            params.append(execution_info_update_json)

        if response is not None:
            response_json = json.dumps(response)
            sql += ", response = %s"
            params.append(response_json)

        sql += " WHERE id = %s;"
        params.append(job_id)

        cursor.execute(sql, tuple(params))
        logger.info(f"Updated job {job_id} status to {status.value}.")
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")
    finally:
        cursor.close()