from typing import Any, Dict

from services.rag_service import answer_question


def rag_agent(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    RAG Agent.

    Uses the existing GSVAI RAG pipeline to answer
    knowledge-based questions contained in emails.
    """

    # ---------------------------------------------------------
    # 1. Get the email content
    # ---------------------------------------------------------

    subject = email.get("subject") or ""
    body = email.get("body") or ""

    # Combine subject and body into the RAG query.
    question = f"""
Subject:
{subject}

Email:
{body}
""".strip()

    # ---------------------------------------------------------
    # 2. Execute existing RAG pipeline
    # ---------------------------------------------------------

    rag_result = answer_question(
        question=question,
        top_k=5,
    )

    # ---------------------------------------------------------
    # 3. Return agent result
    # ---------------------------------------------------------

    return {
        "agent": "rag_agent",
        "status": "COMPLETED",
        "action": "rag_answer_generated",
        "email_id": email.get("email_id"),
        "answer": rag_result.get(
            "answer"
        ),
        "sources": rag_result.get(
            "sources",
            []
        ),
    }