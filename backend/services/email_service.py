from datetime import datetime
from uuid import uuid4
import json

from models.email_models import EmailCreateRequest, EmailResponse

from repositories.email_repository import EmailRepository
from repositories.email_analysis_repository import EmailAnalysisRepository

from services.email_analyzer import analyze_email
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
            message_id=None,
            sender_email=request.sender_email,
            recipient_email=request.recipient_email,
            cc_email=request.cc_email,
            subject=request.subject,
            body=request.body,
            received_date=received_date,
        )

        email = self.repository.get_email(
            email_id
        )

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

        email = self.repository.get_email(
            email_id
        )

        if not email:
            raise ValueError(
                f"Email not found: {email_id}"
            )

        return EmailResponse(**email)

    # =========================================================
    # Analyze Email
    # =========================================================

    def analyze_email_by_id(
        self,
        email_id: str
    ) -> dict:
        """
        Retrieve an email, analyze it using the OCI LLM,
        and persist the AI analysis.
        """

        # ---------------------------------------------------------
        # 1. Retrieve email
        # ---------------------------------------------------------

        email = self.repository.get_email(
            email_id
        )

        if not email:
            raise ValueError(
                f"Email not found: {email_id}"
            )

        # ---------------------------------------------------------
        # 2. Send email to AI analyzer
        # ---------------------------------------------------------

        analysis = analyze_email(
            email
        )

        if not analysis:
            raise RuntimeError(
                f"AI analysis returned no result for email: {email_id}"
            )

        # ---------------------------------------------------------
        # 3. Generate analysis ID
        # ---------------------------------------------------------

        analysis_id = (
            f"ANALYSIS-{uuid4().hex[:12].upper()}"
        )

        # ---------------------------------------------------------
        # 4. Extract structured AI data
        # ---------------------------------------------------------

        extracted_data = analysis.get(
            "extracted_data"
        )

        if extracted_data is not None:
            extracted_data_json = json.dumps(
                extracted_data
            )
        else:
            extracted_data_json = None

        # ---------------------------------------------------------
        # 5. Store AI analysis in Oracle
        # ---------------------------------------------------------

        self.analysis_repository.create_analysis(
            analysis_id=analysis_id,
            email_id=email_id,
            email_type=analysis.get(
                "email_type"
            ),
            priority=analysis.get(
                "priority"
            ),
            confidence=analysis.get(
                "confidence"
            ),
            extracted_data=extracted_data_json,
            recommended_action=analysis.get(
                "recommended_action"
            ),
            reasoning_summary=analysis.get(
                "reasoning_summary"
            ),
        )

        # ---------------------------------------------------------
        # 6. Retrieve saved analysis
        # ---------------------------------------------------------

        saved_analysis = (
            self.analysis_repository.get_analysis(
                email_id
            )
        )

        if not saved_analysis:
            raise RuntimeError(
                "Analysis was created but could not "
                f"be retrieved for email: {email_id}"
            )

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

        If no analysis exists, analyze the email first.
        """

        # ---------------------------------------------------------
        # 1. Retrieve email
        # ---------------------------------------------------------

        email = self.repository.get_email(
            email_id
        )

        if not email:
            raise ValueError(
                f"Email not found: {email_id}"
            )

        # ---------------------------------------------------------
        # 2. Reuse existing analysis
        # ---------------------------------------------------------

        analysis = (
            self.analysis_repository.get_analysis(
                email_id
            )
        )

        # ---------------------------------------------------------
        # 3. Analyze only if no analysis exists
        # ---------------------------------------------------------

        if not analysis:
            analysis = self.analyze_email_by_id(
                email_id
            )

        # ---------------------------------------------------------
        # 4. Route email to appropriate agent
        # ---------------------------------------------------------

        routing_result = route_email(
            email=email,
            analysis=analysis,
        )

        # ---------------------------------------------------------
        # 5. Return complete result
        # ---------------------------------------------------------

        return {
            "email_id": email_id,
            "analysis": analysis,
            "routing": routing_result,
        }