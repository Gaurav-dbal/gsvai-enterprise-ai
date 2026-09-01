from datetime import datetime

from repositories.email_repository import EmailRepository


def main():
    repository = EmailRepository()

    email_id = "TEST-EMAIL-001"

    repository.create_email(
        email_id=email_id,
        message_id="MSG-001",
        sender_email="supplier@example.com",
        recipient_email="ap@company.com",
        cc_email=None,
        subject="Test Invoice",
        body="This is a test invoice email.",
        received_date=datetime.now(),
    )

    print(f"Email created: {email_id}")

    email = repository.get_email(email_id)

    if email:
        print("Email retrieved successfully:")
        print(email)
    else:
        print("Email not found.")


if __name__ == "__main__":
    main()