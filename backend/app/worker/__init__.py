"""Background worker — task definitions and worker settings."""

from app.worker.tasks.ai_jobs import process_ai_job

WORKER_FUNCTIONS = [process_ai_job]

__all__ = ["WORKER_FUNCTIONS", "process_ai_job"]
