import uuid
import time
import json
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database


class BatchTrainingManager:
    def __init__(self):
        initialize_database()

    def create_batch_job(self, sources: List[str]) -> str:
        job_id = f"batch_{uuid.uuid4().hex[:12]}"
        total = len(sources)
        with connect() as c:
            c.execute(
                """
                INSERT INTO batch_training_jobs (
                    job_id, status, total_sources, processed_sources,
                    successful_sources, failed_sources, current_source
                ) VALUES (?, 'pending', ?, 0, 0, 0, '')
                """,
                (job_id, total)
            )
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        with connect() as c:
            row = c.execute("SELECT * FROM batch_training_jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                return {"job_id": job_id, "found": False}
            return dict(row)

    def run_batch_job(self, job_id: str, sources: List[str], pipeline_service) -> Dict[str, Any]:
        with connect() as c:
            c.execute("UPDATE batch_training_jobs SET status='running', updated_at=CURRENT_TIMESTAMP WHERE job_id=?", (job_id,))

        processed = 0
        successful = 0
        failed = 0

        for source in sources:
            with connect() as c:
                c.execute(
                    "UPDATE batch_training_jobs SET current_source=?, updated_at=CURRENT_TIMESTAMP WHERE job_id=?",
                    (source, job_id)
                )

            try:
                res = pipeline_service.train_file(source)
                if res:
                    successful += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            
            processed += 1
            with connect() as c:
                c.execute(
                    """
                    UPDATE batch_training_jobs
                    SET processed_sources=?, successful_sources=?, failed_sources=?, updated_at=CURRENT_TIMESTAMP
                    WHERE job_id=?
                    """,
                    (processed, successful, failed, job_id)
                )

        final_status = "completed" if failed == 0 else ("partial" if successful > 0 else "failed")
        with connect() as c:
            c.execute(
                """
                UPDATE batch_training_jobs
                SET status=?, completed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE job_id=?
                """,
                (final_status, job_id)
            )

        return self.get_job_status(job_id)
