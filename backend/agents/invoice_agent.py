from typing import Any, Dict


def invoice_agent(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Invoice Agent.

    Determines the next action for an invoice-related email
    using the existing GSVAI invoice processing capabilities.
    """

    extracted_data = analysis.get(
        "extracted_data",
        {}
    )

    attachments = email.get(
        "attachments",
        []
    )

    # ---------------------------------------------------------
    # 1. Check whether an invoice attachment exists
    # ---------------------------------------------------------

    if not attachments:

        return {
            "agent": "invoice_agent",
            "status": "WAITING_FOR_ATTACHMENT",
            "action": "route_to_human_review",
            "message": (
                "The email was classified as an invoice, "
                "but no invoice attachment was provided."
            ),
            "email_id": email.get("email_id"),
            "invoice_information": extracted_data,
        }

    # ---------------------------------------------------------
    # 2. Invoice attachment found
    # ---------------------------------------------------------

    return {
        "agent": "invoice_agent",
        "status": "READY_FOR_PROCESSING",
        "action": "process_invoice_attachment",
        "message": (
            "Invoice attachment detected. "
            "Ready to send the document to the existing "
            "GSVAI invoice processing pipeline."
        ),
        "email_id": email.get("email_id"),
        "attachments": attachments,
        "invoice_information": extracted_data,
    }