from enum import Enum


class JobStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    FAILED = "failed" # Added for compatibility with Celery's states