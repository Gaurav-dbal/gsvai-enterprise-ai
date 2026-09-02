from datetime import datetime
from uuid import uuid4
import json
from typing import Any, Dict, List, Optional

from models.email_models import EmailCreateRequest, EmailResponse
from repositories.email_repository import EmailRepository
from repositories.email_analysis_repository import EmailAnalysisRepository
from services.email_analyzer import analyze_email, OCIThrottledException
from services.agent_router_service import route_email


class EmailService:
    """Business logic for email automation."""

    def __init__(self):
        self.repository = EmailRepository()
        self.analysis_repository = EmailAnalysisRepository()

    # =========================================================
    # Create Email
    # =========================================================

    def create_email(
        self,
        request: EmailCreateRequest
    ) -> EmailResponse:
        """Create and persist a new email."""
        email_id = f"EMAIL-{uuid4().hex[:12].upper()}"

        received_date = (
            request.received_date
            or datetime.now()
        )

        self.repository.create_email(
            email_id=email_id,
            message_id=request.message_id,
            sender_email=request.sender_email,
            recipient_email=request.recipient_email,
            cc_email=request.cc_email,
            subject=request.subject,
            body=request.body,
            received_date=received_date,
            status="RECEIVED",
        )

        email = self.repository.get_email(email_id)
        if not email:
            raise RuntimeError(
                f"Email was created but could not be retrieved: {email_id}"
            )

        return EmailResponse(**email)

    # =========================================================
    # Get Email
    # =========================================================

    def get_email(
        self,
        email_id: str
    ) -> EmailResponse:
        """Retrieve an email by ID."""
        email = self.repository.get_email(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        analysis = self.analysis_repository.get_analysis(email_id)
        if analysis and analysis.get("extracted_data"):
            if isinstance(analysis["extracted_data"], str):
                try:
                    analysis["extracted_data"] = json.loads(analysis["extracted_data"])
                except Exception:
                    pass
        email["analysis"] = analysis

        return EmailResponse(**email)

    def get_email_full(self, email_id: str) -> dict:
        """Retrieve complete email record with parsed JSON analysis."""
        email = self.repository.get_email(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        analysis = self.analysis_repository.get_analysis(email_id)
        if analysis and analysis.get("extracted_data"):
            if isinstance(analysis["extracted_data"], str):
                try:
                    analysis["extracted_data"] = json.loads(analysis["extracted_data"])
                except Exception:
                    pass
        email["analysis"] = analysis
        return email

    def list_emails(self, limit: int = 100) -> List[dict]:
        """List emails with their respective analysis attached."""
        emails = self.repository.list_emails(limit=limit)
        for em in emails:
            aid = em.get("email_id")
            if aid:
                analysis = self.analysis_repository.get_analysis(aid)
                if analysis and analysis.get("extracted_data"):
                    if isinstance(analysis["extracted_data"], str):
                        try:
                            analysis["extracted_data"] = json.loads(analysis["extracted_data"])
                        except Exception:
                            pass
                em["analysis"] = analysis
        return emails

    def get_email_counts(self) -> dict:
        """Returns aggregate inbox counts."""
        return self.repository.get_email_counts()

    # =========================================================
    # Analyze Email
    # =========================================================

    def analyze_email_by_id(
        self,
        email_id: str
    ) -> dict:
        """
        Retrieve an email, analyze it using the OCI LLM,
        and persist the AI analysis. Handles OCI 429 throttling gracefully.
        """
        email = self.repository.get_email(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        try:
            analysis = analyze_email(email)
        except OCIThrottledException as te:
            error_msg = str(te)
            self.repository.update_email(
                email_id,
                status="AI_THROTTLED",
                error_message=error_msg,
            )
            return {
                "status": "AI_THROTTLED",
                "email_id": email_id,
                "error_message": error_msg,
                "throttled": True,
            }

        if not analysis:
            raise RuntimeError(
                f"AI analysis returned no result for email: {email_id}"
            )

        analysis_id = f"ANALYSIS-{uuid4().hex[:12].upper()}"
        extracted_data = analysis.get("extracted_data")
        extracted_data_json = json.dumps(extracted_data) if extracted_data is not None else None

        self.analysis_repository.create_analysis(
            analysis_id=analysis_id,
            email_id=email_id,
            email_type=analysis.get("email_type"),
            priority=analysis.get("priority"),
            confidence=analysis.get("confidence"),
            extracted_data=extracted_data_json,
            recommended_action=analysis.get("recommended_action"),
            reasoning_summary=analysis.get("reasoning_summary"),
        )

        self.repository.update_email(
            email_id,
            status="ANALYZED",
            error_message=None,
        )

        saved_analysis = self.analysis_repository.get_analysis(email_id)
        if not saved_analysis:
            raise RuntimeError(
                f"Analysis created but could not be retrieved: {email_id}"
            )

        if saved_analysis.get("extracted_data") and isinstance(saved_analysis["extracted_data"], str):
            try:
                saved_analysis["extracted_data"] = json.loads(saved_analysis["extracted_data"])
            except Exception:
                pass

        return saved_analysis

    # =========================================================
    # Route Email
    # =========================================================

    def route_email_by_id(
        self,
        email_id: str,
    ) -> dict:
        """
        Route an email using its existing AI analysis.
        """
        email = self.repository.get_email(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        analysis = self.analysis_repository.get_analysis(email_id)
        if not analysis:
            analysis = self.analyze_email_by_id(email_id)
            if analysis.get("throttled"):
                return {
                    "email_id": email_id,
                    "status": "AI_THROTTLED",
                    "analysis": analysis,
                    "routing": {"status": "AI_THROTTLED", "message": analysis.get("error_message")},
                }

        routing_result = route_email(
            email=email,
            analysis=analysis,
        )

        # Update routed agent and action on email record
        agent_name = routing_result.get("agent") or routing_result.get("status")
        action = routing_result.get("action") or analysis.get("recommended_action")

        updates: Dict[str, Any] = {
            "routed_agent": agent_name,
            "routing_action": action,
        }

        # Check if RAG agent returned an answer or sources
        if routing_result.get("answer"):
            updates["suggested_reply"] = routing_result["answer"]
            updates["status"] = "AWAITING_APPROVAL"
        elif routing_result.get("throttled"):
            updates["status"] = "AI_THROTTLED"
            updates["error_message"] = routing_result.get("error_message")
        else:
            updates["status"] = "ROUTED"

        if routing_result.get("sources"):
            updates["rag_sources"] = routing_result["sources"]

        self.repository.update_email(email_id, **updates)

        return {
            "email_id": email_id,
            "analysis": analysis,
            "routing": routing_result,
        }