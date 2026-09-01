from typing import Optional

from services.oracle_db_service import get_connection


class EmailRepository:
    """Database operations for email automation."""

    def create_email(
        self,
        email_id: str,
        message_id: Optional[str],
        sender_email: str,
        recipient_email: Optional[str],
        cc_email: Optional[str],
        subject: Optional[str],
        body: Optional[str],
        received_date,
    ) -> None:
        """Insert an incoming email into EMAIL table."""

        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                INSERT INTO EMAIL (
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE
                )
                VALUES (
                    :email_id,
                    :message_id,
                    :sender_email,
                    :recipient_email,
                    :cc_email,
                    :subject,
                    :body,
                    :received_date
                )
            """

            cursor.execute(
                sql,
                {
                    "email_id": email_id,
                    "message_id": message_id,
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "cc_email": cc_email,
                    "subject": subject,
                    "body": body,
                    "received_date": received_date,
                },
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

    def get_email(self, email_id: str) -> Optional[dict]:
        """Retrieve an email by EMAIL_ID."""

        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    EMAIL_ID,
                    MESSAGE_ID,
                    SENDER_EMAIL,
                    RECIPIENT_EMAIL,
                    CC_EMAIL,
                    SUBJECT,
                    BODY,
                    RECEIVED_DATE,
                    STATUS,
                    CREATED_DATE,
                    UPDATED_DATE
                FROM EMAIL
                WHERE EMAIL_ID = :email_id
            """

            cursor.execute(sql, {"email_id": email_id})

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "email_id": row[0],
                "message_id": row[1],
                "sender_email": row[2],
                "recipient_email": row[3],
                "cc_email": row[4],
                "subject": row[5],
                "body": row[6],
                "received_date": row[7],
                "status": row[8],
                "created_date": row[9],
                "updated_date": row[10],
            }

        finally:
            cursor.close()
            connection.close()