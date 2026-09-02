from typing import Any, Dict
import re

from services.rag_service import answer_question, build_rag_context


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
    Uses the existing GSVAI RAG pipeline to answer
    knowledge-based questions contained in emails.
    Handles OCI HTTP 429 throttling gracefully while preserving retrieved sources.
    """
    subject = email.get("subject") or ""
    body = _clean_text(email.get("body") or "")

    question = f"""
Subject:
{subject}

Email:
{body[:2500]}
""".strip()

    try:
        rag_result = answer_question(
            question=question,
            top_k=5,
        )

        return {
            "agent": "rag_agent",
            "status": "COMPLETED",
            "action": "rag_answer_generated",
            "email_id": email.get("email_id"),
            "answer": rag_result.get("answer"),
            "sources": rag_result.get("sources", []),
            "throttled": False,
        }

    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "throttl" in err_str or "too many requests" in err_str:
            # Semantic search can still retrieve the real documents
            sources = []
            try:
                _, retrieved_sources = build_rag_context(question, top_k=5)
                sources = retrieved_sources
            except Exception:
                pass

            return {
                "agent": "rag_agent",
                "status": "AI_THROTTLED",
                "action": "rag_processing_throttled",
                "email_id": email.get("email_id"),
                "answer": None,
                "sources": sources,
                "throttled": True,
                "error_message": "OCI Generative AI is temporarily throttled (HTTP 429). Oracle AI Vector Search retrieved relevant knowledge, but LLM response drafting is temporarily queued.",
            }
        raise