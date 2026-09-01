"""
GSVAI Enterprise AI Platform
Dashboard Live Telemetry & Analytics Service
Queries live Oracle Autonomous Database and real OCI AI audit logs.
No hard-coded numbers, mock arrays, or simulated telemetry.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from services.oracle_db_service import get_connection


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format a datetime into a human-readable relative time string."""
    if not dt:
        return "Recently"
    now = datetime.now()
    if dt.tzinfo:
        # If timezone-aware, compare with UTC or localized now
        now = datetime.now(dt.tzinfo)
    
    diff_secs = (now - dt).total_seconds()
    if diff_secs < 0:
        diff_secs = 0

    if diff_secs < 45:
        return "Just now"
    elif diff_secs < 90:
        return "1 min ago"
    elif diff_secs < 3600:
        mins = int(diff_secs // 60)
        return f"{mins} mins ago"
    elif diff_secs < 7200:
        return "1 hour ago"
    elif diff_secs < 86400:
        hours = int(diff_secs // 3600)
        return f"{hours} hours ago"
    elif diff_secs < 172800:
        return "Yesterday"
    else:
        days = int(diff_secs // 86400)
        return f"{days} days ago"


def get_dashboard_overview(period: str = "today") -> Dict[str, Any]:
    """
    Retrieves consolidated, real operational metrics from Oracle Autonomous Database
    and live audit logs.
    """
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Total Documents Indexed in Vector DB
        cur.execute("SELECT COUNT(*) FROM GSVAI_DOCUMENTS")
        total_documents_row = cur.fetchone()
        total_documents = total_documents_row[0] if total_documents_row else 0

        # Vector Chunks Count
        cur.execute("SELECT COUNT(*) FROM GSVAI_DOCUMENT_CHUNKS")
        chunks_row = cur.fetchone()
        vector_chunks_count = chunks_row[0] if chunks_row else 0

        # 2. Invoices Automated vs In Review vs Exceptions
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN STATUS IN ('APPROVED', 'FUSION_CREATED') THEN 1 END) AS automated_cnt,
                COUNT(CASE WHEN STATUS = 'REVIEW_REQUIRED' THEN 1 END) AS review_cnt,
                COUNT(CASE WHEN STATUS IN ('REJECTED', 'FAILED') THEN 1 END) AS failed_cnt,
                COUNT(CASE WHEN STATUS IN ('PROCESSING', 'UPLOADING') THEN 1 END) AS extraction_cnt,
                COUNT(*) AS total_cnt
            FROM GSVAI_INVOICES
        """)
        inv_row = cur.fetchone()
        if inv_row:
            automated_cnt = inv_row[0] or 0
            review_cnt = inv_row[1] or 0
            failed_cnt = inv_row[2] or 0
            extraction_cnt = inv_row[3] or 0
            total_invoices = inv_row[4] or 0
        else:
            automated_cnt = review_cnt = failed_cnt = extraction_cnt = total_invoices = 0

        # 3. AI Queries & Operational Activity from Audit Logs
        cur.execute("""
            SELECT 
                LOG_ID, ACTION, RESOURCE_TYPE, RESOURCE_ID, DETAILS_JSON, STATUS, CREATED_AT
            FROM GSVAI_AUDIT_LOGS
            ORDER BY CREATED_AT DESC
        """)
        audit_rows = cur.fetchall()

        ai_query_logs = []
        recent_activities = []
        hourly_counts: Dict[str, List[float]] = {}

        now = datetime.now()
        today_date = now.date()

        for r in audit_rows:
            log_id, action, res_type, res_id, details_str, status, created_at = r
            details = {}
            if details_str:
                try:
                    details = json.loads(details_str) if isinstance(details_str, str) else details_str
                except Exception:
                    pass

            # Filter and capture AI queries
            if action == "DATA_ASSISTANT_QUERY":
                exec_time = float(details.get("execution_time_ms") or 0.0)
                ai_query_logs.append({
                    "created_at": created_at,
                    "exec_time": exec_time,
                })

                # Group for throughput chart
                if created_at:
                    if period == "today":
                        # Only include today's queries
                        if created_at.date() == today_date:
                            hour_key = created_at.strftime("%H:00")
                            hourly_counts.setdefault(hour_key, []).append(exec_time)
                    else:
                        hour_key = created_at.strftime("%b %d %H:00")
                        hourly_counts.setdefault(hour_key, []).append(exec_time)

            # Build human-friendly recent activity stream
            rel_time = format_relative_time(created_at)
            raw_time_str = created_at.isoformat() if created_at else None

            title = action.replace("_", " ").title()
            desc = f"{res_type or 'System'}: {res_id or 'General'}"
            if action == "DATA_ASSISTANT_QUERY":
                q_text = details.get("question") or ""
                title = "Data Assistant Query Executed"
                desc = f'"{q_text[:42]}..."' if len(q_text) > 42 else (f'"{q_text}"' if q_text else "Real-time Text-to-SQL execution")
            elif action == "INVOICE_SUBMITTED_TO_FUSION":
                inv_num = res_id or details.get("invoice_id")
                title = f"Invoice #{inv_num} Submitted to Fusion"
                desc = "Synchronized to Oracle Fusion Cloud ERP Payables"
            elif action == "INVOICE_APPROVED":
                inv_num = res_id or details.get("invoice_id")
                title = f"Invoice #{inv_num} Approved"
                desc = "Human review verified and approved for ERP sync"
            elif action == "INVOICE_CORRECTIONS_SAVED":
                inv_num = res_id or details.get("invoice_id")
                title = f"Invoice #{inv_num} Corrections Saved"
                desc = details.get("comments") or "User adjustments verified in database"
            elif action == "INVOICE_REJECTED":
                inv_num = res_id or details.get("invoice_id")
                title = f"Invoice #{inv_num} Rejected"
                desc = f"Reason: {details.get('reason', 'Exception flagged')}"
            elif action == "FUSION_CONNECTION_TESTED":
                title = f"Fusion Connection Tested"
                desc = f"Environment: {details.get('environment', 'Oracle Fusion Cloud ERP')}"

            if len(recent_activities) < 7:
                recent_activities.append({
                    "id": log_id,
                    "title": title,
                    "desc": desc,
                    "time": rel_time,
                    "raw_time": raw_time_str,
                    "status": status or "Completed",
                })

        # Calculate AI latency metrics
        latencies = [x["exec_time"] for x in ai_query_logs if x["exec_time"] > 0]
        avg_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
        min_latency_ms = round(min(latencies), 1) if latencies else 0.0
        max_latency_ms = round(max(latencies), 1) if latencies else 0.0

        # Construct AI Throughput Series
        ai_throughput = []
        if hourly_counts:
            sorted_hours = sorted(hourly_counts.keys())
            for h in sorted_hours:
                l_list = hourly_counts[h]
                avg_h_lat = round(sum(l_list) / len(l_list), 1) if l_list else 0.0
                ai_throughput.append({
                    "time": h,
                    "queries": len(l_list),
                    "latency": round(avg_h_lat / 1000, 2) if avg_h_lat > 0 else 0.0, # in seconds for recharts or ms
                    "latency_ms": avg_h_lat,
                })

        # Construct Document Processing Pipeline
        document_pipeline = [
            {
                "name": "Vendor Invoices",
                "category": "Vendor Invoices",
                "processed": automated_cnt,
                "pending": review_cnt + extraction_cnt,
                "failed": failed_cnt,
                "total": total_invoices,
            },
            {
                "name": "Enterprise Knowledge Docs",
                "category": "Enterprise Knowledge Docs",
                "processed": total_documents,
                "pending": 0,
                "failed": 0,
                "total": total_documents,
            },
        ]

        # Construct Workflow Health
        if total_invoices > 0:
            completed_pct = round((automated_cnt / total_invoices) * 100, 1)
            pending_pct = round((review_cnt / total_invoices) * 100, 1)
            extraction_pct = round((extraction_cnt / total_invoices) * 100, 1)
            exceptions_pct = round((failed_cnt / total_invoices) * 100, 1)
        else:
            completed_pct = pending_pct = extraction_pct = exceptions_pct = 0.0

        workflow_health = {
            "has_data": total_invoices > 0,
            "total_records": total_invoices,
            "items": [
                {
                    "name": "Completed / Synced",
                    "count": automated_cnt,
                    "value": completed_pct,
                    "color": "#12B76A",
                },
                {
                    "name": "Pending Review",
                    "count": review_cnt,
                    "value": pending_pct,
                    "color": "#F79009",
                },
                {
                    "name": "In Extraction",
                    "count": extraction_cnt,
                    "value": extraction_pct,
                    "color": "#2563EB",
                },
                {
                    "name": "Flagged Exceptions",
                    "count": failed_cnt,
                    "value": exceptions_pct,
                    "color": "#F04438",
                },
            ]
        }

        return {
            "status": "success",
            "db_status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_documents": total_documents,
                "total_documents_source": "Oracle Vector DB (GSVAI_DOCUMENTS & GSVAI_DOCUMENT_CHUNKS)",
                "vector_chunks_count": vector_chunks_count,
                "invoices_automated": automated_cnt,
                "invoices_automated_source": "GSVAI_INVOICES (Status: APPROVED, FUSION_CREATED)",
                "invoices_in_review": review_cnt,
                "invoices_in_review_source": "GSVAI_INVOICES (Status: REVIEW_REQUIRED)",
                "ai_queries_count": len(ai_query_logs),
                "ai_queries_source": "GSVAI_AUDIT_LOGS (Action: DATA_ASSISTANT_QUERY)",
                "ai_model_name": "Cohere Command A",
                "ai_model_id": "cohere.command-a-03-2025",
                "avg_latency_ms": avg_latency_ms,
                "min_latency_ms": min_latency_ms,
                "max_latency_ms": max_latency_ms,
            },
            # Top-level backwards compatibility fields for existing frontend bindings
            "total_documents": total_documents,
            "invoices_automated": automated_cnt,
            "invoices_in_review": review_cnt,
            "ai_queries_count": len(ai_query_logs),
            "ai_throughput": ai_throughput,
            "ai_throughput_period": period,
            "document_pipeline": document_pipeline,
            "recent_activities": recent_activities,
            "workflow_health": workflow_health,
        }

    except Exception as e:
        print(f"Error in get_dashboard_overview: {e}")
        # Return strict error state with zero data instead of fake mock numbers
        return {
            "status": "error",
            "db_status": "disconnected",
            "error_message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_documents": 0,
                "total_documents_source": "Database Unavailable",
                "vector_chunks_count": 0,
                "invoices_automated": 0,
                "invoices_automated_source": "Database Unavailable",
                "invoices_in_review": 0,
                "invoices_in_review_source": "Database Unavailable",
                "ai_queries_count": 0,
                "ai_queries_source": "Database Unavailable",
                "ai_model_name": "Cohere Command A",
                "ai_model_id": "cohere.command-a-03-2025",
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
            },
            "total_documents": 0,
            "invoices_automated": 0,
            "invoices_in_review": 0,
            "ai_queries_count": 0,
            "ai_throughput": [],
            "ai_throughput_period": period,
            "document_pipeline": [],
            "recent_activities": [],
            "workflow_health": {
                "has_data": False,
                "total_records": 0,
                "items": [],
            },
        }
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
