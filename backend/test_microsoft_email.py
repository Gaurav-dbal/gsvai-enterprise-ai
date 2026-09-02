from services.microsoft_email_service import MicrosoftEmailService


def main():
    print("Connecting to Microsoft mailbox...")

    service = MicrosoftEmailService()

    service.authenticate()

    print("\nReading unread emails...\n")

    messages = service.get_unread_messages(top=10)

    if not messages:
        print("No unread emails found.")
        return

    print(f"Found {len(messages)} unread email(s).\n")

    for i, message in enumerate(messages, start=1):
        print("=" * 70)
        print(f"EMAIL {i}")
        print("=" * 70)

        print("Message ID :", message.get("id"))
        print("Subject    :", message.get("subject"))

        sender = message.get("from", {}).get("emailAddress", {})
        print("From       :", sender.get("name"))
        print("Email      :", sender.get("address"))

        print("Received   :", message.get("receivedDateTime"))

        body = message.get("body", {})
        print("\nBody:")
        print(body.get("content", ""))

        print()


if __name__ == "__main__":
    main()