import datetime
import threading
from typing import Any, Dict, Optional


class InvoiceStateManager:
    """
    Thread-safe in-memory state manager for asynchronous invoice processing jobs.
    Tracks pipeline stages, real-time progress percentages, OCI job references,
    and extracted invoice payloads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(
        self,
        processing_id: str,
        filename: str,
        file_size: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            task_data = {
                "processing_id": processing_id,
                "filename": filename,
                "file_size": file_size,
                "status": "UPLOADED",
                "stage": "UPLOADING",
                "progress": 10,
                "message": "Invoice PDF received and validated.",
                "job_id": None,
                "object_name": None,
                "created_at": now,
                "updated_at": now,
                "error": None,
                "result": None,
            }
            self._tasks[processing_id] = task_data
            return dict(task_data)

    def update_task(
        self,
        processing_id: str,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        job_id: Optional[str] = None,
        object_name: Optional[str] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(processing_id)
            if not task:
                return None

            now = datetime.datetime.utcnow().isoformat() + "Z"
            task["updated_at"] = now

            if stage is not None:
                task["stage"] = stage
            if status is not None:
                task["status"] = status
            if progress is not None:
                task["progress"] = min(100, max(0, int(progress)))
            if message is not None:
                task["message"] = message
            if job_id is not None:
                task["job_id"] = job_id
            if object_name is not None:
                task["object_name"] = object_name
            if error is not None:
                task["error"] = str(error)
                task["status"] = "FAILED"
                task["stage"] = "FAILED"
            if result is not None:
                task["result"] = result
                task["status"] = "COMPLETED"
                task["stage"] = "COMPLETED"
                task["progress"] = 100

            return dict(task)

    def get_status(self, processing_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(processing_id)
            if not task:
                return None
            return {
                "processing_id": task["processing_id"],
                "filename": task["filename"],
                "file_size": task["file_size"],
                "status": task["status"],
                "stage": task["stage"],
                "progress": task["progress"],
                "message": task["message"],
                "job_id": task["job_id"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "error": task["error"],
            }

    def get_result(self, processing_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(processing_id)
            if not task:
                return None
            return task.get("result")

    def get_task(self, processing_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(processing_id)
            if not task:
                return None
            return dict(task)


# Global singleton instance
invoice_state_manager = InvoiceStateManager()
