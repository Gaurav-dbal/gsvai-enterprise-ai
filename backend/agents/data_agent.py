import re
from typing import Any, Dict

from services.data_assistant_service import process_data_assistant_query
from services.oci_llm_service import generate_general_answer
from services.ai_runtime_config import get_ai_runtime_config, format_rate_limit_error


def _clean_text(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def data_agent(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Data Agent.
    Interprets natural language data, metrics, or reporting questions in emails,
    queries the Oracle database via GSVAI Data Assistant, and drafts an executive
    response with data insights for operator review.
    """
    subject = email.get("subject") or ""
    body = _clean_text(email.get("body") or "")
    email_id = email.get("email_id")

    query_text = f"{subject}. {body}".strip()

    try:
        # Step 1: Attempt Text-to-SQL query against active Oracle database
        query_result = process_data_assistant_query(
            question=query_text[:1000],
            user_id="email_automation_agent",
        )

        ai_cfg = get_ai_runtime_config()
        llm_provider = ai_cfg["llm"]["provider"]
        llm_model = ai_cfg["llm"]["model"]

        if query_result.get("status") == "success" and query_result.get("data"):
            data_rows = query_result.get("data", [])[:10]
            columns = query_result.get("columns", [])
            sql = query_result.get("sql", "")
            explanation = query_result.get("explanation", "")

            prompt = f"""
You are an enterprise AI communication assistant for GSVAI.
An employee or customer sent an email inquiring about business data:
Subject: {subject}
Message: {body[:1500]}

The GSVAI Data Assistant executed the following verified read-only SQL query against the Oracle Autonomous Database:
SQL: {sql}
Explanation: {explanation}
Returned Rows (up to 10): {data_rows}

Draft a clear, professional, executive email reply summarizing this data accurately.
Mention that the numbers are retrieved live from the enterprise database.
Do not invent unstated metrics.
"""
            answer = generate_general_answer(question=prompt)
            return {
                "agent": "data_agent",
                "status": "COMPLETED",
                "action": "data_query_answered",
                "email_id": email_id,
                "answer": answer,
                "sql": sql,
                "data_rows_count": len(data_rows),
                "throttled": False,
            }

        # If data query could not execute cleanly or was general analytics guidance
        prompt = f"""
You are an enterprise AI communication assistant for GSVAI.
An incoming email requested database or reporting assistance:
Subject: {subject}
Message: {body[:2000]}

Draft a professional, helpful email response acknowledging their inquiry.
Explain that their request has been logged and is being reviewed by the enterprise analytics team.
If relevant, outline the standard metrics or data sources available.
Sign off professionally as 'GSVAI Enterprise Intelligence Support'.
"""
        answer = generate_general_answer(question=prompt)
        return {
            "agent": "data_agent",
            "status": "COMPLETED",
            "action": "data_query_assisted",
            "email_id": email_id,
            "answer": answer,
            "sql": query_result.get("sql"),
            "throttled": False,
        }

    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "throttl" in err_str or "rate limit" in err_str:
            return {
                "agent": "data_agent",
                "status": "AI_THROTTLED",
                "action": "data_processing_throttled",
                "email_id": email_id,
                "answer": None,
                "throttled": True,
                "error_message": format_rate_limit_error(),
            }
        raise
