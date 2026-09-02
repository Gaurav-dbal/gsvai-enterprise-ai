import json
import re

from services.oci_llm_service import generate_answer


class OCIThrottledException(Exception):
    """Raised when OCI Generative AI is temporarily throttled with HTTP 429."""
    pass


EMAIL_ANALYSIS_PROMPT = """
You are an enterprise email analysis assistant for GSVAI.

Analyze the email provided below.

Your tasks are:

1. Classify the email into EXACTLY ONE of:
   - invoice
   - purchase_order
   - customer_query
   - hr
   - technical_issue
   - general
   - unknown

2. Determine priority:
   - low
   - medium
   - high
   - critical

3. Extract relevant information from the email.

4. Recommend the next action:
   - route_to_invoice_agent
   - route_to_rag_agent
   - route_to_data_agent
   - route_to_human_review
   - no_action

5. Provide a short reasoning summary.

IMPORTANT:
- Do not invent information.
- If a field is not present, return null.
- Confidence must be a number between 0 and 1.
- Return ONLY valid JSON.
- Do not include markdown.
- Do not include ```json or ```.

Return exactly this structure:

{{
    "email_type": "invoice",
    "priority": "medium",
    "confidence": 0.95,
    "extracted_data": {{
        "vendor": null,
        "customer": null,
        "invoice_number": null,
        "po_number": null,
        "amount": null,
        "currency": null,
        "employee_name": null,
        "request_type": null,
        "urgency": null,
        "attachment_information": []
    }},
    "recommended_action": "route_to_invoice_agent",
    "reasoning_summary": "Short explanation"
}}

EMAIL INFORMATION
=================

Sender:
{sender_email}

Recipient:
{recipient_email}

Subject:
{subject}

Body:
{body}

Attachments:
{attachments}
"""


def _clean_body_text(text: str) -> str:
    """Helper to strip noisy HTML tags and collapse whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def analyze_email(email: dict) -> dict:
    """
    Analyze an email using the existing GSVAI OCI LLM service.
    Catches OCI HTTP 429 throttling gracefully.
    """
    raw_body = email.get("body") or ""
    clean_body = _clean_body_text(raw_body)

    prompt = EMAIL_ANALYSIS_PROMPT.format(
        sender_email=email.get("sender_email") or "",
        recipient_email=email.get("recipient_email") or "",
        subject=email.get("subject") or "",
        body=clean_body[:4000],
        attachments=email.get("attachments") or [],
    )

    try:
        response = generate_answer(
            question=prompt,
            context=""
        )
    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "throttl" in err_str or "too many requests" in err_str:
            raise OCIThrottledException(
                "OCI Generative AI is temporarily throttled (HTTP 429). Request preserved for retry."
            ) from exc
        raise

    if not response:
        raise RuntimeError(
            "OCI LLM returned an empty response."
        )

    response = response.strip()

    # Remove markdown code fences if the LLM adds them.
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]

    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    try:
        analysis = json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"OCI LLM returned invalid JSON: {response}"
        ) from exc

    return analysis