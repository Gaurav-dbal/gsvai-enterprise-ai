import json
import time
from typing import Any, Dict, List, Optional
import oracledb

from services.oracle_db_service import get_connection
from services.auth_rbac_service import log_audit_event


def sanitize_trace_details(obj: Any) -> Any:
    """Recursively strip any sensitive keys or credentials from trace objects."""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(forbidden in k_lower for forbidden in [
                "pass", "secret", "key", "token", "auth", "credential", "wallet", "api_key", "groq_api_key"
            ]):
                continue
            clean[k] = sanitize_trace_details(v)
        return clean
    elif isinstance(obj, list):
        return [sanitize_trace_details(item) for item in obj]
    return obj


def record_ai_request(
    request_id: str,
    provider: str,
    model: str,
    serving_mode: str = "PRIMARY",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: float = 0.0,
    status: str = "SUCCESS",
    fallback: bool = False,
    fallback_reason: Optional[str] = None,
    rag_used: bool = False,
    retrieval_latency_ms: float = 0.0,
    retrieval_count: int = 0,
    citation_count: int = 0,
    route: str = "GENERAL_AI",
    error_message: Optional[str] = None,
    trace: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Persists real-time AI request telemetry into GSVAI_AI_OBSERVABILITY.
    """
    safe_trace_json = None
    if trace:
        try:
            safe_trace = sanitize_trace_details(trace)
            safe_trace_json = json.dumps(safe_trace, default=str)
        except Exception:
            safe_trace_json = None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO GSVAI_AI_OBSERVABILITY (
                REQUEST_ID,
                PROVIDER,
                MODEL,
                SERVING_MODE,
                INPUT_TOKENS,
                OUTPUT_TOKENS,
                TOTAL_TOKENS,
                LATENCY_MS,
                STATUS,
                FALLBACK,
                FALLBACK_REASON,
                RAG_USED,
                RETRIEVAL_LATENCY_MS,
                RETRIEVAL_COUNT,
                CITATION_COUNT,
                ROUTE,
                ERROR_MESSAGE,
                TRACE_JSON,
                CREATED_AT
            )
            VALUES (
                :request_id,
                :provider,
                :model,
                :serving_mode,
                :input_tokens,
                :output_tokens,
                :total_tokens,
                :latency_ms,
                :status,
                :fallback,
                :fallback_reason,
                :rag_used,
                :retrieval_latency_ms,
                :retrieval_count,
                :citation_count,
                :route,
                :error_message,
                :trace_json,
                SYSTIMESTAMP
            )
            """,
            request_id=request_id,
            provider=provider,
            model=model,
            serving_mode=serving_mode,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            total_tokens=int(total_tokens or (input_tokens + output_tokens)),
            latency_ms=round(float(latency_ms or 0.0), 2),
            status=status,
            fallback=1 if fallback else 0,
            fallback_reason=fallback_reason,
            rag_used=1 if rag_used else 0,
            retrieval_latency_ms=round(float(retrieval_latency_ms or 0.0), 2),
            retrieval_count=int(retrieval_count or 0),
            citation_count=int(citation_count or 0),
            route=route,
            error_message=error_message[:500] if error_message else None,
            trace_json=safe_trace_json,
        )
        conn.commit()
    except Exception as e:
        print(f"Warning: Failed to record observability telemetry: {e}")
    finally:
        cursor.close()
        conn.close()


def get_observability_summary() -> Dict[str, Any]:
    """
    Calculates summary observability metrics from GSVAI_AI_OBSERVABILITY.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_req,
                NVL(SUM(CASE WHEN STATUS = 'SUCCESS' THEN 1 ELSE 0 END), 0) AS success_req,
                NVL(SUM(CASE WHEN STATUS IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END), 0) AS failed_req,
                NVL(SUM(CASE WHEN STATUS = 'BLOCKED' THEN 1 ELSE 0 END), 0) AS blocked_req,
                NVL(SUM(CASE WHEN FALLBACK = 1 THEN 1 ELSE 0 END), 0) AS fallback_req,
                NVL(AVG(CASE WHEN STATUS = 'SUCCESS' THEN LATENCY_MS ELSE NULL END), 0) AS avg_latency,
                NVL(SUM(INPUT_TOKENS), 0) AS sum_input_tokens,
                NVL(SUM(OUTPUT_TOKENS), 0) AS sum_output_tokens,
                NVL(SUM(TOTAL_TOKENS), 0) AS sum_total_tokens,
                NVL(SUM(CASE WHEN RAG_USED = 1 THEN 1 ELSE 0 END), 0) AS rag_req,
                NVL(SUM(CASE WHEN RETRIEVAL_COUNT > 0 THEN 1 ELSE 0 END), 0) AS retrieval_req
            FROM GSVAI_AI_OBSERVABILITY
            """
        )
        row = cursor.fetchone()
        total_req = int(row[0] or 0)
        success_req = int(row[1] or 0)
        failed_req = int(row[2] or 0)
        blocked_req = int(row[3] or 0)
        fallback_req = int(row[4] or 0)
        avg_latency = round(float(row[5] or 0.0), 2)
        sum_input_tokens = int(row[6] or 0)
        sum_output_tokens = int(row[7] or 0)
        sum_total_tokens = int(row[8] or 0)
        rag_req = int(row[9] or 0)
        retrieval_req = int(row[10] or 0)

        # Calculate p95 latency
        p95_latency = 0.0
        if total_req > 0:
            cursor.execute(
                """
                SELECT LATENCY_MS
                FROM (
                    SELECT LATENCY_MS, PERCENT_RANK() OVER (ORDER BY LATENCY_MS ASC) as pr
                    FROM GSVAI_AI_OBSERVABILITY
                    WHERE STATUS = 'SUCCESS'
                )
                WHERE pr >= 0.95
                FETCH FIRST 1 ROWS ONLY
                """
            )
            p95_row = cursor.fetchone()
            if p95_row and p95_row[0] is not None:
                p95_latency = round(float(p95_row[0]), 2)
            else:
                p95_latency = avg_latency

        providers = get_provider_metrics()

        return {
            "total_requests": total_req,
            "successful_requests": success_req,
            "failed_requests": failed_req,
            "blocked_requests": blocked_req,
            "fallback_requests": fallback_req,
            "fallback_requests_count": fallback_req,
            "success_rate_pct": round((success_req / total_req * 100), 1) if total_req > 0 else 100.0,
            "fallback_rate_pct": round((fallback_req / total_req * 100), 1) if total_req > 0 else 0.0,
            "average_latency_ms": avg_latency,
            "avg_latency_ms": avg_latency,
            "total_tokens": sum_total_tokens,
            "total_prompt_tokens": sum_input_tokens,
            "total_completion_tokens": sum_output_tokens,
            "provider_breakdown": providers,
            "tokens": {
                "input_tokens": sum_input_tokens,
                "output_tokens": sum_output_tokens,
                "total_tokens": sum_total_tokens,
            },
            "rag": {
                "rag_requests": rag_req,
                "retrieval_requests": retrieval_req,
            },
        }
    finally:
        cursor.close()
        conn.close()


def get_recent_requests(
    limit: int = 50,
    provider: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Returns recent AI requests with execution telemetry.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        where_clauses = []
        params = {"lim": int(limit)}

        if provider and provider.strip() and provider.lower() != "all":
            where_clauses.append("LOWER(PROVIDER) = :provider")
            params["provider"] = provider.strip().lower()

        if status and status.strip() and status.lower() != "all":
            where_clauses.append("LOWER(STATUS) = :status")
            params["status"] = status.strip().lower()

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(
            f"""
            SELECT
                ID,
                REQUEST_ID,
                CREATED_AT,
                PROVIDER,
                MODEL,
                SERVING_MODE,
                INPUT_TOKENS,
                OUTPUT_TOKENS,
                TOTAL_TOKENS,
                LATENCY_MS,
                STATUS,
                FALLBACK,
                FALLBACK_REASON,
                RAG_USED,
                RETRIEVAL_LATENCY_MS,
                RETRIEVAL_COUNT,
                CITATION_COUNT,
                ROUTE,
                ERROR_MESSAGE
            FROM GSVAI_AI_OBSERVABILITY
            {where_sql}
            ORDER BY ID DESC
            FETCH FIRST :lim ROWS ONLY
            """,
            **params
        )

        rows = cursor.fetchall()
        results = []
        for r in rows:
            created_str = r[2].isoformat() + "Z" if hasattr(r[2], "isoformat") else str(r[2] or "")
            results.append({
                "id": r[0],
                "request_id": r[1],
                "timestamp": created_str,
                "provider": r[3],
                "model": r[4],
                "serving_mode": r[5],
                "input_tokens": int(r[6] or 0),
                "output_tokens": int(r[7] or 0),
                "total_tokens": int(r[8] or 0),
                "latency_ms": float(r[9] or 0.0),
                "status": r[10],
                "fallback": bool(r[11]),
                "fallback_reason": r[12],
                "rag_used": bool(r[13]),
                "retrieval_latency_ms": float(r[14] or 0.0),
                "retrieval_count": int(r[15] or 0),
                "citation_count": int(r[16] or 0),
                "route": r[17] or "GENERAL_AI",
                "error_message": r[18],
            })
        return results
    finally:
        cursor.close()
        conn.close()


def get_provider_metrics() -> List[Dict[str, Any]]:
    """
    Returns breakdown of usage, tokens, latency, and fallback events by LLM provider.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                PROVIDER,
                COUNT(*) AS req_count,
                NVL(SUM(CASE WHEN STATUS = 'SUCCESS' THEN 1 ELSE 0 END), 0) AS success_count,
                NVL(SUM(CASE WHEN STATUS IN ('FAILED', 'ERROR') THEN 1 ELSE 0 END), 0) AS failed_count,
                NVL(SUM(CASE WHEN FALLBACK = 1 THEN 1 ELSE 0 END), 0) AS fallback_count,
                NVL(AVG(CASE WHEN STATUS = 'SUCCESS' THEN LATENCY_MS ELSE NULL END), 0) AS avg_latency,
                NVL(SUM(TOTAL_TOKENS), 0) AS sum_tokens
            FROM GSVAI_AI_OBSERVABILITY
            WHERE PROVIDER IS NOT NULL
            GROUP BY PROVIDER
            ORDER BY req_count DESC
            """
        )
        rows = cursor.fetchall()
        providers = []
        for r in rows:
            req_c = int(r[1] or 0)
            succ_c = int(r[2] or 0)
            providers.append({
                "provider": r[0],
                "requests": req_c,
                "successful": succ_c,
                "failed": int(r[3] or 0),
                "fallback_activations": int(r[4] or 0),
                "success_rate_pct": round((succ_c / req_c * 100), 1) if req_c > 0 else 100.0,
                "average_latency_ms": round(float(r[5] or 0.0), 2),
                "total_tokens": int(r[6] or 0),
            })

        # Ensure both primary and fallback providers have representations
        known_providers = {p["provider"].lower(): p for p in providers}
        if "groq" not in known_providers:
            providers.insert(0, {
                "provider": "Groq",
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "fallback_activations": 0,
                "success_rate_pct": 100.0,
                "average_latency_ms": 0.0,
                "total_tokens": 0,
            })
        if "ollama" not in known_providers:
            providers.append({
                "provider": "Ollama",
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "fallback_activations": 0,
                "success_rate_pct": 100.0,
                "average_latency_ms": 0.0,
                "total_tokens": 0,
            })

        return providers
    finally:
        cursor.close()
        conn.close()


def get_request_trace(request_id: str, user_id: str = "admin") -> Optional[Dict[str, Any]]:
    """
    Retrieves the execution trace JSON for a given request ID.
    Audits the inspection event.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT TRACE_JSON, PROVIDER, MODEL, LATENCY_MS, STATUS, ROUTE
            FROM GSVAI_AI_OBSERVABILITY
            WHERE REQUEST_ID = :req_id
            """,
            req_id=request_id
        )
        row = cursor.fetchone()
        if not row:
            return None

        trace_raw = row[0]
        trace_data = None
        if trace_raw:
            try:
                trace_content = trace_raw.read() if hasattr(trace_raw, "read") else trace_raw
                trace_data = json.loads(trace_content)
            except Exception:
                trace_data = {"error": "Failed to decode trace JSON."}

        log_audit_event(
            action="AI_TRACE_VIEWED",
            resource_type="AI_OBSERVABILITY",
            resource_id=request_id,
            user_id=user_id,
            details={
                "provider": row[1],
                "model": row[2],
                "status": row[4],
                "route": row[5],
            }
        )

        return {
            "request_id": request_id,
            "provider": row[1],
            "model": row[2],
            "latency_ms": float(row[3] or 0.0),
            "status": row[4],
            "route": row[5],
            "trace": trace_data,
        }
    finally:
        cursor.close()
        conn.close()
