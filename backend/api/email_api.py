from fastapi import APIRouter, HTTPException, status

from models.email_models import EmailCreateRequest, EmailResponse
from services.email_service import EmailService


router = APIRouter(
    prefix="/api/emails",
    tags=["Email Automation"],
)

email_service = EmailService()


@router.post(
    "",
    response_model=EmailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_email(request: EmailCreateRequest):
    """Receive and store a new email."""

    try:
        return email_service.create_email(request)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create email: {str(exc)}",
        )


@router.get(
    "/{email_id}",
    response_model=EmailResponse,
)
def get_email(email_id: str):
    """Retrieve an email by ID."""

    try:
        return email_service.get_email(email_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve email: {str(exc)}",
        )