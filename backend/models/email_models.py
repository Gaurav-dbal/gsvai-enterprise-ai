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
    created_date: datetime
    updated_date: datetime


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