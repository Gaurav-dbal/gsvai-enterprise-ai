import json

from services.oci_llm_service import generate_answer


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


def analyze_email(email: dict) -> dict:
    """
    Analyze an email using the existing GSVAI OCI LLM service.
    """

    prompt = EMAIL_ANALYSIS_PROMPT.format(
        sender_email=email.get("sender_email") or "",
        recipient_email=email.get("recipient_email") or "",
        subject=email.get("subject") or "",
        body=email.get("body") or "",
        attachments=email.get("attachments") or [],
    )

    # Reuse the existing GSVAI OCI LLM implementation.
    response = generate_answer(
        question=prompt,
        context=""
    )

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