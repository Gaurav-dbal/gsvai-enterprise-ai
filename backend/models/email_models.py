from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# EMAIL MODELS
# ============================================================

class EmailCreateRequest(BaseModel):
    """Request model for receiving a new email."""

    sender_email: str = Field(..., max_length=320)
    recipient_email: Optional[str] = Field(None, max_length=320)
    cc_email: Optional[str] = Field(None, max_length=2000)
    subject: Optional[str] = Field(None, max_length=1000)
    body: Optional[str] = None
    received_date: Optional[datetime] = None
    message_id: Optional[str] = Field(None, max_length=500)


class EmailResponse(BaseModel):
    """Response model representing an email."""

    model_config = ConfigDict(from_attributes=True)

    email_id: str
    message_id: Optional[str] = None
    sender_email: str
    recipient_email: Optional[str] = None
    cc_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    received_date: Optional[datetime] = None
    status: str
    routed_agent: Optional[str] = None
    routing_action: Optional[str] = None
    suggested_reply: Optional[str] = None
    rag_sources: Optional[Any] = None
    trace_data: Optional[Any] = None
    error_message: Optional[str] = None
    reply_text: Optional[str] = None
    reply_sent_at: Optional[datetime] = None
    created_date: datetime
    updated_date: datetime
    analysis: Optional[dict[str, Any]] = None


class EmailApproveReplyRequest(BaseModel):
    """Request model for approving and sending an email reply."""

    reply_text: str = Field(..., min_length=1, description="The human-approved reply text to send via Microsoft Graph")


class EmailRejectRequest(BaseModel):
    """Request model for rejecting an email draft or routing to manual review."""

    reason: Optional[str] = "Sent to manual review by operator"


class EmailInboxSummary(BaseModel):
    """Real-time summary counters for email automation inbox."""

    total_count: int = 0
    unread_count: int = 0
    processed_count: int = 0
    awaiting_approval_count: int = 0
    replies_sent_count: int = 0
    throttled_count: int = 0
    last_sync: Optional[str] = None


# ============================================================
# EMAIL ANALYSIS MODELS
# ============================================================

class ExtractedEmailData(BaseModel):
    """Structured information extracted from an email."""

    vendor: Optional[str] = None
    customer: Optional[str] = None
    invoice_number: Optional[str] = None
    po_number: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    employee_name: Optional[str] = None
    request_type: Optional[str] = None
    urgency: Optional[str] = None
    attachment_information: Optional[list[str]] = None


class EmailAnalysisResponse(BaseModel):
    """AI analysis result for an email."""

    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    email_id: str
    email_type: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[float] = None
    extracted_data: Optional[dict[str, Any]] = None
    recommended_action: Optional[str] = None
    reasoning_summary: Optional[str] = None
    analyzed_date: datetime