from typing import Any, Dict
import re

from services.rag_service import build_rag_context
from services.oci_llm_service import generate_answer, generate_general_answer
from services.ai_runtime_config import get_ai_runtime_config, format_rate_limit_error


def _clean_text(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def rag_agent(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    RAG Agent.
    Uses the active GSVAI RAG pipeline to answer
    knowledge-based questions contained in emails.
    Guarantees exactly ONE vector search execution per processing request.
    Handles rate-limiting gracefully while preserving retrieved sources.
    """
    subject = email.get("subject") or ""
    body = _clean_text(email.get("body") or "")

    question = f"""
Subject:
{subject}

Email:
{body[:2500]}
""".strip()

    # Step 1: Execute semantic vector search exactly once
    context, sources = build_rag_context(
        query=question,
        top_k=5,
    )

    if not context:
        try:
            fallback_prompt = f"""
You are an enterprise AI communication assistant for GSVAI Enterprise Support.
An incoming email was received:
Subject: {subject}
Message: {body[:2000]}

Draft a professional, courteous, and helpful response email:
1. Acknowledge their specific issue or question with empathy.
2. Provide clear standard preliminary troubleshooting steps or guidance applicable to this inquiry (e.g., verifying credentials, system status check, browser cache clearing, or standard support process).
3. State that an enterprise support specialist is reviewing the request and will follow up with any required resolution details.
4. Sign off professionally as 'GSVAI Enterprise Support Team'.

Do not invent ticket numbers. Keep the tone helpful, reassuring, and enterprise-grade.
"""
            fallback_draft = generate_general_answer(question=fallback_prompt)
            return {
                "agent": "rag_agent",
                "status": "COMPLETED",
                "action": "rag_general_support_draft",
                "email_id": email.get("email_id"),
                "answer": fallback_draft,
                "sources": [],
                "throttled": False,
            }
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "throttl" in err_str or "rate limit" in err_str:
                return {
                    "agent": "rag_agent",
                    "status": "AI_THROTTLED",
                    "action": "rag_processing_throttled",
                    "email_id": email.get("email_id"),
                    "answer": None,
                    "sources": [],
                    "throttled": True,
                    "error_message": format_rate_limit_error(),
                }
            raise

    # Step 2: Generate response using active LLM
    try:
        answer = generate_answer(
            question=question,
            context=context,
        )

        return {
            "agent": "rag_agent",
            "status": "COMPLETED",
            "action": "rag_answer_generated",
            "email_id": email.get("email_id"),
            "answer": answer,
            "sources": sources,
            "throttled": False,
        }

    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "throttl" in err_str or "too many requests" in err_str or "rate limit" in err_str:
            ai_cfg = get_ai_runtime_config()
            vdb_name = ai_cfg["vector_database"]["provider"]
            err_msg = format_rate_limit_error()

            return {
                "agent": "rag_agent",
                "status": "AI_THROTTLED",
                "action": "rag_processing_throttled",
                "email_id": email.get("email_id"),
                "answer": None,
                "sources": sources,  # Preserves already retrieved sources without duplicate search
                "throttled": True,
                "error_message": f"{err_msg} {vdb_name} retrieved relevant knowledge, but response drafting is temporarily queued.",
            }
        raise