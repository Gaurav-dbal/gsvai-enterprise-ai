import time
from typing import Any, Dict, List, Optional
import datetime

# Import actual model IDs from services to avoid hardcoding
try:
    from services.oci_embedding_service import MODEL_ID as EMBEDDING_MODEL_ID
except Exception:
    EMBEDDING_MODEL_ID = "cohere.embed-v4.0"

try:
    from services.oci_llm_service import MODEL_ID as LLM_MODEL_ID
except Exception:
    LLM_MODEL_ID = "cohere.command-a-03-2025"


class ExecutionTracer:
    """
    Collects real-time execution telemetry and educational explanations
    during AI Workspace query processing.
    """

    def __init__(self, query: str, scope: Optional[str] = "all", document_id: Optional[int] = None):
        self.start_time = time.perf_counter()
        self.query = query
        self.scope = scope
        self.document_id = document_id
        self.route = "UNKNOWN"
        self.route_label = "Unknown Route"
        self.rag_used = False
        self.steps: List[Dict[str, Any]] = []
        self.step_counter = 1

    def add_step(
        self,
        name: str,
        status: str,  # 'completed' | 'skipped' | 'failed'
        duration_ms: float,
        explanation: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Adds an instrumented execution step."""
        clean_details = {}
        if details:
            for k, v in details.items():
                if v is not None and not any(
                    secret in k.lower()
                    for secret in ["pass", "secret", "key", "token", "auth", "ocid", "credential"]
                ):
                    clean_details[k] = v

        self.steps.append({
            "step": self.step_counter,
            "name": name,
            "status": status,
            "duration_ms": max(1, round(duration_ms, 1)),
            "explanation": explanation,
            "details": clean_details,
        })
        self.step_counter += 1

    def to_dict(self) -> Dict[str, Any]:
        """Returns the serialized trace structure."""
        total_duration = (time.perf_counter() - self.start_time) * 1000
        return {
            "enabled": True,
            "total_duration_ms": round(total_duration, 1),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "query": self.query,
            "route": self.route,
            "route_label": self.route_label,
            "rag_used": self.rag_used,
            "steps_count": len(self.steps),
            "steps": self.steps,
        }
