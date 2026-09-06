from typing import Any, Dict

from services.oci_llm_service import generate_general_answer


def invoice_agent(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Invoice Agent.

    Handles invoice-related emails and produces a customer-facing
    response draft using the configured Groq LLM.

    Human approval is still required before the response is sent.
    """

    extracted_data = analysis.get(
        "extracted_data",
        {}
    )

    attachments = email.get(
        "attachments",
        []
    )

    subject = email.get(
        "subject",
        ""
    )

    sender = email.get(
        "sender_email",
        ""
    )

    # ---------------------------------------------------------
    # 1. Check whether an invoice attachment exists
    # ---------------------------------------------------------

    if not attachments:

        draft_prompt = f"""
You are an enterprise invoice-support assistant.

An email was classified as an invoice, but no invoice attachment
was available.

Create a short, professional customer-facing email asking the
sender to resend the invoice with the attachment.

Email sender: {sender}
Subject: {subject}

Do not mention AI, Groq, internal systems, or technical details.

Return only the email response text.
"""

        try:
            answer = generate_general_answer(
                question=draft_prompt
            )
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "throttl" in err_str or "rate limit" in err_str:
                from services.ai_runtime_config import format_rate_limit_error
                return {
                    "agent": "invoice_agent",
                    "status": "AI_THROTTLED",
                    "action": "invoice_processing_throttled",
                    "email_id": email.get("email_id"),
                    "answer": None,
                    "throttled": True,
                    "error_message": format_rate_limit_error(),
                    "invoice_information": extracted_data,
                }
            raise

        return {
            "agent": "invoice_agent",
            "status": "WAITING_FOR_ATTACHMENT",
            "action": "route_to_human_review",
            "message": (
                "The email was classified as an invoice, "
                "but no invoice attachment was provided."
            ),
            "answer": answer,
            "email_id": email.get("email_id"),
            "invoice_information": extracted_data,
        }

    # ---------------------------------------------------------
    # 2. Invoice attachment found
    # ---------------------------------------------------------

    attachment_names = ", ".join(
        str(item) for item in attachments
    )

    draft_prompt = f"""
You are an enterprise invoice-support assistant.

An invoice email has been received and an invoice attachment
is available.

Create a short, professional customer-facing acknowledgement
confirming receipt of the invoice and that it will be reviewed
by the finance team.

Email sender: {sender}
Subject: {subject}
Attachments: {attachment_names}

Invoice information:
{extracted_data}

Do not mention AI, Groq, internal systems, or technical details.

Do not promise payment or approval.

Return only the email response text.
"""

    try:
        answer = generate_general_answer(
            question=draft_prompt
        )
    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "throttl" in err_str or "rate limit" in err_str:
            from services.ai_runtime_config import format_rate_limit_error
            return {
                "agent": "invoice_agent",
                "status": "AI_THROTTLED",
                "action": "invoice_processing_throttled",
                "email_id": email.get("email_id"),
                "answer": None,
                "throttled": True,
                "error_message": format_rate_limit_error(),
                "attachments": attachments,
                "invoice_information": extracted_data,
            }
        raise

    return {
        "agent": "invoice_agent",
        "status": "READY_FOR_PROCESSING",
        "action": "process_invoice_attachment",
        "message": (
            "Invoice attachment detected. "
            "Ready to send the document to the existing "
            "GSVAI invoice processing pipeline."
        ),
        "answer": answer,
        "email_id": email.get("email_id"),
        "attachments": attachments,
        "invoice_information": extracted_data,
    }