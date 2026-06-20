import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class JobRecord:
    id: str
    name: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    result: dict | None = None
    error: str | None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(self, name: str, fn: Callable[[], dict]) -> str:
        job_id = uuid.uuid4().hex
        job = JobRecord(id=job_id, name=name)
        with self._lock:
            self._jobs[job_id] = job

        def runner() -> None:
            with self._lock:
                job.status = "running"
            try:
                result = fn()
                with self._lock:
                    job.status = "completed"
                    job.result = result
                    job.finished_at = datetime.now(timezone.utc).isoformat()
            except Exception as exc:
                with self._lock:
                    job.status = "failed"
                    job.error = str(exc)
                    job.finished_at = datetime.now(timezone.utc).isoformat()

        threading.Thread(target=runner, daemon=True).start()
        return job_id

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": job.id,
                    "name": job.name,
                    "status": job.status,
                    "created_at": job.created_at,
                    "finished_at": job.finished_at,
                    "error": job.error,
                }
                for job in self._jobs.values()
            ]


job_manager = JobManager()
